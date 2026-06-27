from pathlib import Path

import cv2
import numpy as np
import pytest

from aicutting.core.artifacts import write_json_model, write_json_models
from aicutting.core.models import (
    DroneShotType,
    LocationTitle,
    Timeline,
    TimelineClip,
    Transition,
    TransitionType,
)
from aicutting.director.edit_models import (
    Director3Report,
    EditClip,
    EditDecision,
    MomentRating,
    RhythmSlot,
)
from aicutting.director.models import LocationSuggestion
from aicutting.report import build_report


def _write_tiny_video(path: Path) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 5.0, (64, 48))
    if not writer.isOpened():
        pytest.skip("OpenCV cannot write MJPG test videos in this environment")
    for index in range(15):
        writer.write(np.full((48, 64, 3), index * 15, dtype=np.uint8))
    writer.release()


def _two_clip_timeline(video: Path) -> Timeline:
    return Timeline(
        target_duration_s=4.0,
        fps=25.0,
        width=1920,
        height=1080,
        title=LocationTitle(title="Madeira Coast", subtitle="June 2025", confidence=0.9),
        clips=[
            TimelineClip(
                asset_path=video,
                source_start_s=0.2,
                source_end_s=2.2,
                timeline_start_s=0.0,
                transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0.0),
                speed=1.0,
                color_intent="neutral",
            ),
            TimelineClip(
                asset_path=video,
                source_start_s=1.0,
                source_end_s=2.0,
                timeline_start_s=2.0,
                transition_in=Transition(kind=TransitionType.SMOOTH_ZOOM, duration_s=0.4),
                speed=1.0,
                color_intent="warm",
            ),
        ],
    )


def _write_full_artifacts(output_dir: Path, video: Path) -> None:
    write_json_model(output_dir / "timeline.json", _two_clip_timeline(video))
    write_json_models(
        output_dir / "footage-ratings.json",
        [
            MomentRating(
                moment_id="m001",
                cinematic_score=0.91,
                shot_type=DroneShotType.REVEAL,
                keep=True,
                reason="clean reveal over the ridgeline",
            ),
            MomentRating(
                moment_id="m002",
                cinematic_score=0.28,
                shot_type=DroneShotType.UNSTABLE,
                keep=False,
                reason="too shaky on the descent",
            ),
        ],
    )
    write_json_models(
        output_dir / "rhythm-grid.json",
        [
            RhythmSlot(
                index=0, start_s=0.0, end_s=2.0, energy=0.4, is_accent=False, section="intro"
            ),
            RhythmSlot(
                index=1, start_s=2.0, end_s=4.0, energy=0.95, is_accent=True, section="peak"
            ),
        ],
    )
    write_json_model(
        output_dir / "edit-decision.json",
        EditDecision(
            arc="calm build to a coastal reveal",
            clips=[
                EditClip(
                    slot_index=0,
                    moment_id="m001",
                    effect=TransitionType.HARD_CUT,
                    reason="open on the ridge",
                ),
                EditClip(
                    slot_index=1,
                    moment_id="m001",
                    effect=TransitionType.SMOOTH_ZOOM,
                    reason="land the accent",
                ),
            ],
        ),
    )
    write_json_model(
        output_dir / "director-3-report.json",
        Director3Report(
            used_agent=True,
            backend="codex",
            rated_moments=2,
            kept_moments=1,
            timeline_clips=2,
            warnings=[],
        ),
    )
    write_json_models(
        output_dir / "location-suggestions.json",
        [
            LocationSuggestion(
                title="Madeira Coast",
                place="Madeira, Portugal",
                confidence=0.88,
                evidence=["terraced coastline", "volcanic sea cliffs"],
                should_render=True,
            )
        ],
    )


def test_build_report_renders_full_artifacts(tmp_path: Path) -> None:
    video = tmp_path / "clip.avi"
    _write_tiny_video(video)
    _write_full_artifacts(tmp_path, video)

    report_path = build_report(tmp_path)

    assert report_path == tmp_path / "report.html"
    assert report_path.exists()
    html = report_path.read_text(encoding="utf-8")

    # Location title surfaces in the header.
    assert "Madeira Coast" in html
    # The rejected moment's reason is shown in the selection breakdown.
    assert "too shaky on the descent" in html
    # The cut renders one card per timeline clip and reports the clip count.
    assert html.count('class="clip-card"') == 2
    assert "2 clip" in html
    # A real thumbnail was extracted for at least one clip.
    thumbs = list((tmp_path / "report-assets").glob("*.jpg"))
    assert thumbs, "expected at least one extracted thumbnail jpg"


def test_build_report_with_only_timeline(tmp_path: Path) -> None:
    video = tmp_path / "clip.avi"
    _write_tiny_video(video)
    write_json_model(tmp_path / "timeline.json", _two_clip_timeline(video))

    report_path = build_report(tmp_path)

    assert report_path.exists()
    html = report_path.read_text(encoding="utf-8")
    assert "<html" in html.lower()
    assert "Madeira Coast" in html


def test_build_report_escapes_malicious_reason(tmp_path: Path) -> None:
    video = tmp_path / "clip.avi"
    _write_tiny_video(video)
    write_json_model(tmp_path / "timeline.json", _two_clip_timeline(video))
    write_json_models(
        tmp_path / "footage-ratings.json",
        [
            MomentRating(
                moment_id="m001",
                cinematic_score=0.2,
                shot_type=DroneShotType.UNSTABLE,
                keep=False,
                reason="<script>x</script>",
            )
        ],
    )

    report_path = build_report(tmp_path)
    html = report_path.read_text(encoding="utf-8")

    assert "<script>x</script>" not in html
    assert "&lt;script&gt;x&lt;/script&gt;" in html
