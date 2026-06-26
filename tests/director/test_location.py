import json
import subprocess
from pathlib import Path
from typing import Any

from aicutting.agents.backends import AgentBackend
from aicutting.director.location import (
    choose_renderable_title,
    fallback_location_suggestion,
    location_response_schema,
    parse_location_agent_response,
    resolve_location_suggestions,
)
from aicutting.director.models import LocationSuggestion


def test_low_confidence_location_suggestion_is_not_renderable() -> None:
    suggestion = LocationSuggestion(
        title="Some Coast",
        place="unknown",
        confidence=0.4,
        evidence=["agent guess"],
        should_render=True,
    )

    assert choose_renderable_title([suggestion]) is None


def test_high_confidence_location_suggestion_becomes_title() -> None:
    suggestion = LocationSuggestion(
        title="Madeira Coast",
        place="Madeira, Portugal",
        confidence=0.86,
        evidence=["metadata GPS"],
        should_render=True,
    )

    title = choose_renderable_title([suggestion])

    assert title is not None
    assert title.title == "Madeira Coast"
    assert title.subtitle == "Madeira, Portugal"


def test_fallback_location_suggestion_is_safe_and_not_rendered() -> None:
    suggestion = fallback_location_suggestion("no metadata or agent backend available")

    assert suggestion.should_render is False
    assert suggestion.renderable is False


def test_parse_location_agent_response_accepts_fenced_json() -> None:
    raw = """
    The best answer is:
    ```json
    {
      "title": "Madeira Coast",
      "place": "Madeira, Portugal",
      "confidence": 0.82,
      "evidence": ["coastal cliffs", "terraced hills"],
      "should_render": true
    }
    ```
    """

    suggestion = parse_location_agent_response(raw)

    assert suggestion.title == "Madeira Coast"
    assert suggestion.place == "Madeira, Portugal"
    assert suggestion.renderable is True


def test_parse_location_agent_response_handles_claude_json_result_wrapper() -> None:
    raw = json.dumps(
        {
            "type": "result",
            "result": json.dumps(
                {
                    "title": "Unknown Coast",
                    "place": "unknown",
                    "confidence": 0.41,
                    "evidence": ["visual match is too weak"],
                    "should_render": True,
                }
            ),
        }
    )

    suggestion = parse_location_agent_response(raw)

    assert suggestion.should_render is True
    assert suggestion.renderable is False


def test_location_response_schema_requires_safe_fields() -> None:
    schema = location_response_schema()

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "title",
        "place",
        "confidence",
        "evidence",
        "should_render",
    }


def test_resolve_location_suggestions_uses_codex_cmd_for_ps1_backend(
    tmp_path: Path,
) -> None:
    image = tmp_path / "frame.jpg"
    image.write_bytes(b"fake jpg")
    ps1 = tmp_path / "codex.ps1"
    ps1.write_text("", encoding="utf-8")
    cmd = tmp_path / "codex.cmd"
    cmd.write_text("", encoding="utf-8")
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def fake_runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        output_path = Path(command[command.index("--output-last-message") + 1])
        output_path.write_text(
            json.dumps(
                {
                    "title": "Madeira Coast",
                    "place": "Madeira, Portugal",
                    "confidence": 0.9,
                    "evidence": ["distinct volcanic coastline"],
                    "should_render": True,
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    suggestions = resolve_location_suggestions(
        [image],
        [AgentBackend(name="codex", executable=str(ps1), available=True)],
        workdir=tmp_path,
        runner=fake_runner,
    )

    assert suggestions[0].title == "Madeira Coast"
    assert calls[0][0][0] == str(cmd)
    assert calls[0][0].count("--image") == 1
    assert calls[0][0][-1] == "-"
    assert "input" in calls[0][1]


def test_resolve_location_suggestions_falls_back_after_agent_failure(
    tmp_path: Path,
) -> None:
    image = tmp_path / "frame.jpg"
    image.write_bytes(b"fake jpg")

    def failing_runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="agent exploded")

    suggestions = resolve_location_suggestions(
        [image],
        [AgentBackend(name="codex", executable="codex", available=True)],
        workdir=tmp_path,
        runner=failing_runner,
    )

    assert suggestions[0].should_render is False
    assert "codex failed" in suggestions[0].evidence[0]
