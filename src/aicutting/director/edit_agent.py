import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from aicutting.agents.backends import AgentBackend
from aicutting.core.models import DroneShotType
from aicutting.director.edit_models import (
    ContactSheet,
    MomentRating,
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
    on_progress: Callable[[int, int], None] | None = None,
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
            finally:
                if on_progress is not None:
                    on_progress(index, len(sheets))
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
