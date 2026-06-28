"""The pipeline's reveal-landing pass: it slides a clip's source window forward without changing
its duration (so the beat grid is untouched), and is best-effort (any failure leaves the cut)."""

from pathlib import Path

import pytest

from aicutting.core.models import Timeline, TimelineClip, Transition, TransitionType
from aicutting.pipeline import _land_on_reveals


def _timeline() -> Timeline:
    clips = [
        TimelineClip(
            asset_path=Path("a.mp4"),
            source_start_s=17.29,
            source_end_s=20.03,
            timeline_start_s=0.0,
            transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0.0),
            speed=1.0,
            color_intent="subtle_cinematic",
        ),
        TimelineClip(
            asset_path=Path("b.mp4"),
            source_start_s=4.0,
            source_end_s=7.0,
            timeline_start_s=2.74,
            transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0.0),
            speed=1.0,
            color_intent="subtle_cinematic",
        ),
    ]
    return Timeline(target_duration_s=5.74, fps=25.0, width=1920, height=1080, clips=clips)


def test_slides_window_forward_keeping_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("aicutting.pipeline.clip_landing_shifts", lambda clips: [3.89, 0.0])
    out = _land_on_reveals(_timeline())

    shifted = out.clips[0]
    assert (shifted.source_start_s, shifted.source_end_s) == (21.18, 23.92)  # +3.89, both ends
    duration = shifted.source_end_s - shifted.source_start_s
    assert duration == pytest.approx(2.74)  # duration preserved -> beat grid untouched
    assert out.clips[1] == _timeline().clips[1]  # the un-shifted clip is untouched


def test_no_shifts_leaves_the_timeline_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("aicutting.pipeline.clip_landing_shifts", lambda clips: [0.0, 0.0])
    timeline = _timeline()
    assert _land_on_reveals(timeline).clips == timeline.clips


def test_a_read_failure_leaves_the_timeline_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(clips: object) -> list[float]:
        raise OSError("unreadable footage")

    monkeypatch.setattr("aicutting.pipeline.clip_landing_shifts", boom)
    timeline = _timeline()
    assert _land_on_reveals(timeline).clips == timeline.clips
