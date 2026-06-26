import json
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from aicutting.agents.backends import AgentBackend
from aicutting.core.models import LocationTitle
from aicutting.director.models import LocationSuggestion

AgentRunner = Callable[..., subprocess.CompletedProcess[str]]


def location_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["title", "place", "confidence", "evidence", "should_render"],
        "properties": {
            "title": {
                "type": "string",
                "description": "Short, display-ready title. Empty string if uncertain.",
            },
            "place": {
                "type": "string",
                "description": "Specific place name or 'unknown'.",
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
            },
            "evidence": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            },
            "should_render": {
                "type": "boolean",
                "description": "True only when the location is specific enough for a video title.",
            },
        },
    }


def choose_renderable_title(suggestions: list[LocationSuggestion]) -> LocationTitle | None:
    renderable = [suggestion for suggestion in suggestions if suggestion.renderable]
    if not renderable:
        return None
    best = max(renderable, key=lambda suggestion: suggestion.confidence)
    return LocationTitle(title=best.title, subtitle=best.place, confidence=best.confidence)


def fallback_location_suggestion(reason: str) -> LocationSuggestion:
    return LocationSuggestion(
        title="",
        place="unknown",
        confidence=0.0,
        evidence=[reason],
        should_render=False,
    )


def parse_location_agent_response(raw: str) -> LocationSuggestion:
    last_error: Exception | None = None
    for candidate in _candidate_json_payloads(raw):
        try:
            payload = json.loads(candidate)
            suggestion = _suggestion_from_payload(payload)
            if suggestion is not None:
                return suggestion
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            continue

    detail = f": {last_error}" if last_error is not None else ""
    raise ValueError(f"location agent did not return a valid suggestion{detail}")


def build_location_prompt(image_paths: list[Path]) -> str:
    image_list = "\n".join(f"- {path}" for path in image_paths)
    schema = json.dumps(location_response_schema(), ensure_ascii=True)
    return (
        "You are a conservative location title assistant for professional drone edits.\n"
        "Inspect the attached screenshots from the same source footage and identify the "
        "most likely location only when visual evidence is strong.\n"
        "Do not guess from generic scenery. If the place is not specific, return "
        "place='unknown', confidence below 0.75, and should_render=false.\n"
        "Prefer clean title text suitable for a short cinematic overlay.\n\n"
        f"Screenshots:\n{image_list}\n\n"
        f"Return JSON only matching this schema:\n{schema}"
    )


def resolve_location_suggestions(
    image_paths: list[Path],
    backends: list[AgentBackend],
    workdir: Path,
    runner: AgentRunner = subprocess.run,
) -> list[LocationSuggestion]:
    usable_images = [path for path in image_paths if path.exists()]
    if not usable_images:
        return [fallback_location_suggestion("no screenshots available for location agent")]

    available_backends = _preferred_available_backends(backends)
    if not available_backends:
        return [fallback_location_suggestion("no metadata or agent backend available")]

    errors: list[str] = []
    for backend in available_backends:
        try:
            if backend.name == "codex":
                return [_resolve_with_codex(usable_images, backend, workdir, runner)]
            if backend.name == "claude":
                return [_resolve_with_claude(usable_images, backend, workdir, runner)]
            errors.append(f"{backend.name} is not supported for location recognition")
        except Exception as exc:
            errors.append(f"{backend.name} failed: {exc}")

    return [fallback_location_suggestion("; ".join(errors))]


def _resolve_with_codex(
    image_paths: list[Path],
    backend: AgentBackend,
    workdir: Path,
    runner: AgentRunner,
) -> LocationSuggestion:
    workdir.mkdir(parents=True, exist_ok=True)
    schema_path = workdir / "location-agent-schema.json"
    response_path = workdir / "location-agent-response.codex.json"
    schema_path.write_text(json.dumps(location_response_schema(), indent=2), encoding="utf-8")

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
    ]
    for image_path in image_paths:
        command.extend(["--image", str(image_path)])
    command.append("-")

    completed = runner(
        command,
        cwd=str(workdir),
        input=build_location_prompt(image_paths),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=180,
    )
    _raise_for_agent_failure(completed)
    raw = response_path.read_text(encoding="utf-8") if response_path.exists() else completed.stdout
    return parse_location_agent_response(raw)


def _resolve_with_claude(
    image_paths: list[Path],
    backend: AgentBackend,
    workdir: Path,
    runner: AgentRunner,
) -> LocationSuggestion:
    workdir.mkdir(parents=True, exist_ok=True)
    command = [
        _backend_executable(backend),
        "-p",
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(location_response_schema(), ensure_ascii=True),
        build_location_prompt(image_paths),
    ]
    completed = runner(
        command,
        cwd=str(workdir),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=180,
    )
    _raise_for_agent_failure(completed)
    return parse_location_agent_response(completed.stdout)


def _preferred_available_backends(backends: list[AgentBackend]) -> list[AgentBackend]:
    rank = {"codex": 0, "claude": 1}
    return sorted(
        [backend for backend in backends if backend.available and backend.executable],
        key=lambda backend: rank.get(backend.name, 99),
    )


def _backend_executable(backend: AgentBackend) -> str:
    if backend.executable is None:
        raise ValueError(f"{backend.name} executable is missing")

    executable = Path(backend.executable)
    if backend.name == "codex" and executable.suffix.lower() == ".ps1":
        cmd_executable = executable.with_suffix(".cmd")
        if cmd_executable.exists():
            return str(cmd_executable)
    return str(executable)


def _raise_for_agent_failure(completed: subprocess.CompletedProcess[str]) -> None:
    if completed.returncode == 0:
        return

    details = (completed.stderr or completed.stdout or "").strip()
    raise RuntimeError(details or f"exit code {completed.returncode}")


def _candidate_json_payloads(raw: str) -> list[str]:
    payloads: list[str] = []
    stripped = raw.strip()
    if stripped:
        payloads.append(stripped)

    for match in re.finditer(r"```(?:json)?\s*(.*?)```", raw, flags=re.DOTALL | re.IGNORECASE):
        block = match.group(1).strip()
        if block:
            payloads.append(block)

    first = raw.find("{")
    last = raw.rfind("}")
    if first >= 0 and last > first:
        payloads.append(raw[first : last + 1])

    return payloads


def _suggestion_from_payload(payload: Any) -> LocationSuggestion | None:
    if not isinstance(payload, dict):
        return None

    if "title" in payload:
        return LocationSuggestion.model_validate(payload)

    result = payload.get("result")
    if isinstance(result, str):
        return parse_location_agent_response(result)
    if isinstance(result, dict):
        return _suggestion_from_payload(result)

    return None
