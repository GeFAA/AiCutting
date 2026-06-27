import json
import subprocess
from pathlib import Path
from typing import Any

from aicutting.agents.backends import AgentBackend
from aicutting.core.models import DroneShotType
from aicutting.director.edit_models import (
    ContactSheet,
    EditDecision,
    MomentRating,
    RhythmSlot,
)
from aicutting.director.location import (
    AgentRunner,
    _backend_executable,
    _candidate_json_payloads,
    _preferred_available_backends,
    _raise_for_agent_failure,
)

_SHOT_TYPES = [member.value for member in DroneShotType]


def rating_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["ratings"],
        "properties": {
            "ratings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["moment_id", "cinematic_score", "shot_type", "keep", "reason"],
                    "properties": {
                        "moment_id": {"type": "string"},
                        "cinematic_score": {"type": "number", "minimum": 0, "maximum": 1},
                        "shot_type": {"type": "string", "enum": _SHOT_TYPES},
                        "keep": {"type": "boolean"},
                        "reason": {"type": "string"},
                    },
                },
            }
        },
    }


def build_rating_prompt(moment_ids: list[str]) -> str:
    ids = ", ".join(moment_ids)
    return (
        "You are a demanding professional drone-video editor. The attached contact sheet shows "
        "numbered frames, each labelled with its moment id (top-left).\n"
        f"Rate ONLY these moments: {ids}.\n"
        "Give cinematic_score 0-1 and the drone shot_type. A great shot has DEPTH and a focal "
        "point: a visible horizon or sky, layered distance, or a clear subject (mountain, crater "
        "rim, coastline, river, road).\n"
        "Set keep=false AND score below 0.4 for: takeoff or landing; low-altitude or near-ground "
        "shots; the drone descending or hovering low; and -- importantly -- any frame that is "
        "mostly flat ground, rock, lava, gravel or moss texture seen from above with NO horizon "
        "and NO clear subject. That is filler even when the colours or patterns look interesting. "
        "Also reject tilted horizon, shaky or blurry frames, sun glare, and empty sky.\n"
        "Keep ONLY clearly airborne, sharp, well-composed cinematic shots with real depth. Be "
        "very strict -- when in doubt, keep=false.\n"
        "Return JSON only matching the schema."
    )


def parse_ratings_response(raw: str) -> list[MomentRating]:
    for candidate in _candidate_json_payloads(raw):
        try:
            payload = json.loads(candidate)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        ratings = _ratings_from_payload(payload)
        if ratings:
            return ratings
    return []


def _ratings_from_payload(payload: Any) -> list[MomentRating]:
    if isinstance(payload, dict) and isinstance(payload.get("result"), str):
        return parse_ratings_response(payload["result"])
    items = payload.get("ratings") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []
    out: list[MomentRating] = []
    for item in items:
        try:
            out.append(MomentRating.model_validate(item))
        except (TypeError, ValueError):
            continue
    return out


def rate_moments(
    sheets: list[ContactSheet],
    backends: list[AgentBackend],
    workdir: Path,
    runner: AgentRunner = subprocess.run,
) -> list[MomentRating]:
    available = _preferred_available_backends(backends)
    if not available or not sheets:
        return []
    workdir.mkdir(parents=True, exist_ok=True)
    schema_path = workdir / "edit-rating-schema.json"
    schema_path.write_text(json.dumps(rating_schema(), indent=2), encoding="utf-8")
    for backend in available:  # try each backend; fall through if one (e.g. codex) is broken
        ratings: list[MomentRating] = []
        for index, sheet in enumerate(sheets, start=1):
            try:
                ratings.extend(_rate_one(backend, sheet, schema_path, workdir, index, runner))
            except Exception:  # one bad sheet must not abort the batch
                continue
        if ratings:
            return ratings
    return []


def _rate_one(
    backend: AgentBackend,
    sheet: ContactSheet,
    schema_path: Path,
    workdir: Path,
    index: int,
    runner: AgentRunner,
) -> list[MomentRating]:
    prompt = build_rating_prompt(sheet.moment_ids)
    response_path = workdir / f"edit-rating-{index:02d}.json"
    if backend.name == "claude":
        command = [
            _backend_executable(backend),
            "-p",
            "--output-format",
            "json",
            "--json-schema",
            json.dumps(rating_schema(), ensure_ascii=True),
            "--image",
            str(sheet.path),
            prompt,
        ]
        input_text = None
    else:
        command = [
            _backend_executable(backend),
            "exec",
            "--skip-git-repo-check",
            "-s",
            "read-only",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(response_path),
            "--image",
            str(sheet.path),
            "-",
        ]
        input_text = prompt
    completed = runner(
        command,
        cwd=str(workdir),
        input=input_text,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=180,
    )
    _raise_for_agent_failure(completed)
    raw = response_path.read_text(encoding="utf-8") if response_path.exists() else completed.stdout
    return parse_ratings_response(raw)


_EFFECTS = [
    "hard_cut",
    "dissolve",
    "smooth_zoom",
    "whip_blur",
    "flash_cut",
    "speed_ramp",
    "match_motion",
]


def edit_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["arc", "clips"],
        "properties": {
            "arc": {"type": "string"},
            "clips": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["slot_index", "moment_id", "effect", "reason"],
                    "properties": {
                        "slot_index": {"type": "integer", "minimum": 0},
                        "moment_id": {"type": "string"},
                        "effect": {"type": "string", "enum": _EFFECTS},
                        "reason": {"type": "string"},
                    },
                },
            },
        },
    }


def build_edit_prompt(kept: list[MomentRating], slots: list[RhythmSlot]) -> str:
    moments = "\n".join(
        f"- {r.moment_id}: {r.shot_type.value} score {r.cinematic_score:.2f}" for r in kept
    )
    grid = "\n".join(
        f"- slot {s.index}: {s.duration_s:.2f}s energy {s.energy:.2f} "
        f"{'ACCENT ' if s.is_accent else ''}{s.section}"
        for s in slots
    )
    return (
        "You are a professional drone-video editor cutting to music. Fill EVERY slot, in slot "
        "order, so the cut runs the whole song. There are usually fewer good moments than slots, "
        "so REUSE your strongest moments across the song -- this is expected, not a problem.\n"
        "Rules: you may reuse a moment, but never in two adjacent slots and avoid reusing one "
        "within ~5 slots while other moments are still unused; never put the same shot_type in "
        "two adjacent slots; match calm slots to establishing/top_down/orbit and "
        "high-energy/accent slots to reveal/approach/fly_through; build toward the accents.\n"
        "Choose an effect per slot: usually hard_cut; on ACCENT slots, if the motion fits, "
        "use smooth_zoom (forward/reveal), whip_blur (fast lateral), or match_motion; dissolve "
        "only for calm intros/outros. Keep effects rare and tasteful.\n\n"
        f"Available moments ({len(kept)}):\n{moments}\n\nSlots ({len(slots)}):\n{grid}\n\n"
        "Return JSON only matching the schema."
    )


def parse_edit_response(raw: str) -> EditDecision | None:
    for candidate in _candidate_json_payloads(raw):
        try:
            payload = json.loads(candidate)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and isinstance(payload.get("result"), str):
            return parse_edit_response(payload["result"])
        if isinstance(payload, dict) and "clips" in payload:
            try:
                return EditDecision.model_validate(payload)
            except (TypeError, ValueError):
                continue
    return None


def decide_edit(
    kept: list[MomentRating],
    slots: list[RhythmSlot],
    backends: list[AgentBackend],
    workdir: Path,
    runner: AgentRunner = subprocess.run,
) -> EditDecision | None:
    available = _preferred_available_backends(backends)
    if not available or not kept or not slots:
        return None
    workdir.mkdir(parents=True, exist_ok=True)
    schema_path = workdir / "edit-decision-schema.json"
    schema_path.write_text(json.dumps(edit_schema(), indent=2), encoding="utf-8")
    prompt = build_edit_prompt(kept, slots)
    for backend in available:  # try each backend; fall through if one (e.g. codex) is broken
        edit = _decide_one(backend, prompt, schema_path, workdir, runner)
        if edit is not None:
            return edit
    return None


def _decide_one(
    backend: AgentBackend,
    prompt: str,
    schema_path: Path,
    workdir: Path,
    runner: AgentRunner,
) -> EditDecision | None:
    response_path = workdir / f"edit-decision.{backend.name}.json"
    if backend.name == "claude":
        command = [
            _backend_executable(backend),
            "-p",
            "--output-format",
            "json",
            "--json-schema",
            json.dumps(edit_schema(), ensure_ascii=True),
            prompt,
        ]
        input_text = None
    else:
        command = [
            _backend_executable(backend),
            "exec",
            "--skip-git-repo-check",
            "-s",
            "read-only",
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(response_path),
            "-",
        ]
        input_text = prompt
    try:
        completed = runner(
            command,
            cwd=str(workdir),
            input=input_text,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=180,
        )
        _raise_for_agent_failure(completed)
    except Exception:  # fall through to the next backend / deterministic editor
        return None
    raw = response_path.read_text(encoding="utf-8") if response_path.exists() else completed.stdout
    return parse_edit_response(raw)
