import json
import subprocess
from pathlib import Path
from typing import Any

from aicutting.agents.backends import AgentBackend
from aicutting.core.models import DroneShotType, TransitionType
from aicutting.director.edit_agent import (
    decide_edit,
    parse_edit_response,
    parse_ratings_response,
    rate_moments,
    rating_schema,
)
from aicutting.director.edit_models import ContactSheet, MomentRating, RhythmSlot


def test_rating_schema_requires_safe_fields() -> None:
    schema = rating_schema()
    item = schema["properties"]["ratings"]["items"]
    assert item["additionalProperties"] is False
    assert set(item["required"]) == {"moment_id", "cinematic_score", "shot_type", "keep", "reason"}


def test_parse_ratings_accepts_fenced_json() -> None:
    raw = """```json
    {"ratings": [
      {
        "moment_id": "m001", "cinematic_score": 0.9,
        "shot_type": "reveal", "keep": true, "reason": "ok"
      },
      {
        "moment_id": "m002", "cinematic_score": 0.1,
        "shot_type": "takeoff_or_landing", "keep": false, "reason": "landing"
      }
    ]}
    ```"""
    ratings = parse_ratings_response(raw)
    assert [r.moment_id for r in ratings] == ["m001", "m002"]
    assert ratings[1].keep is False


def test_rate_moments_calls_codex_per_sheet(tmp_path: Path) -> None:
    sheet = tmp_path / "contact-sheet-01.jpg"
    sheet.write_bytes(b"img")
    calls: list[list[str]] = []

    def fake_runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        out = Path(command[command.index("--output-last-message") + 1])
        out.write_text(
            json.dumps(
                {
                    "ratings": [
                        {
                            "moment_id": "m001",
                            "cinematic_score": 0.8,
                            "shot_type": "approach",
                            "keep": True,
                            "reason": "ok",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    ratings = rate_moments(
        [ContactSheet(path=sheet, moment_ids=["m001"])],
        [AgentBackend(name="codex", executable="codex", available=True)],
        workdir=tmp_path,
        runner=fake_runner,
    )

    assert ratings[0].moment_id == "m001"
    assert "--image" in calls[0]
    assert str(sheet) in calls[0]


def test_rate_moments_without_backend_returns_empty(tmp_path: Path) -> None:
    sheet = tmp_path / "s.jpg"
    sheet.write_bytes(b"img")
    ratings = rate_moments(
        [ContactSheet(path=sheet, moment_ids=["m001"])],
        [AgentBackend(name="codex", executable=None, available=False)],
        workdir=tmp_path,
    )
    assert ratings == []


def test_parse_edit_response_maps_effects() -> None:
    raw = json.dumps(
        {
            "arc": "build",
            "clips": [
                {"slot_index": 0, "moment_id": "m001", "effect": "hard_cut", "reason": "open"},
                {"slot_index": 1, "moment_id": "m002", "effect": "smooth_zoom", "reason": "peak"},
            ],
        }
    )
    decision = parse_edit_response(raw)
    assert decision is not None
    assert decision.clips[1].effect == TransitionType.SMOOTH_ZOOM


def test_decide_edit_calls_agent_once(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        out = Path(command[command.index("--output-last-message") + 1])
        out.write_text(
            json.dumps(
                {
                    "arc": "x",
                    "clips": [
                        {"slot_index": 0, "moment_id": "m001", "effect": "hard_cut", "reason": "o"}
                    ],
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    kept = [
        MomentRating(
            moment_id="m001",
            cinematic_score=0.9,
            shot_type=DroneShotType.REVEAL,
            keep=True,
            reason="ok",
        )
    ]
    slots = [
        RhythmSlot(index=0, start_s=0.0, end_s=3.0, energy=0.8, is_accent=True, section="peak")
    ]
    decision = decide_edit(
        kept,
        slots,
        [AgentBackend(name="codex", executable="codex", available=True)],
        tmp_path,
        fake_runner,
    )

    assert decision is not None and decision.clips[0].moment_id == "m001"
    assert len(calls) == 1
