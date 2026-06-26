import json
import subprocess
from pathlib import Path
from typing import Any

from aicutting.agents.backends import AgentBackend
from aicutting.core.models import DroneShotType
from aicutting.director.edit_models import ContactSheet, MomentRating
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
        "You are a professional drone-video editor. The attached contact sheet shows numbered "
        "frames, each labelled with its moment id (top-left).\n"
        f"Rate ONLY these moments: {ids}.\n"
        "For each: cinematic_score 0-1 (composition, light, interest), the drone shot_type, and "
        "keep=false for takeoff, landing, search/hunting motion, shaky, blurry, or boring "
        "sky/ground with no subject. Be strict: a clean professional edit needs only the "
        "best moments.\n"
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
    backend = available[0]
    workdir.mkdir(parents=True, exist_ok=True)
    schema_path = workdir / "edit-rating-schema.json"
    schema_path.write_text(json.dumps(rating_schema(), indent=2), encoding="utf-8")
    ratings: list[MomentRating] = []
    for index, sheet in enumerate(sheets, start=1):
        try:
            ratings.extend(_rate_one(backend, sheet, schema_path, workdir, index, runner))
        except Exception:  # one bad sheet must not abort the batch
            continue
    return ratings


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
