import json
from pathlib import Path

import pytest

from aicutting.agents.backends import AgentBackend
from aicutting.core.models import (
    AnalysisReport,
    AudioAnalysis,
    ClipCandidate,
    DroneShotType,
    LocationTitle,
    MediaAsset,
)
from aicutting.core.progress import PipelinePhase, ProgressEvent
from aicutting.director.models import LocationSuggestion
from aicutting.pipeline import (
    CutPipeline,
    PipelineDependencies,
    _compose_title,
    default_analyze,
)


def test_pipeline_writes_artifacts_without_rendering(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    video = input_dir / "clip.mp4"
    video.write_text("", encoding="utf-8")

    report = AnalysisReport(
        media=[MediaAsset(path=video, duration_s=8, width=1920, height=1080, fps=25)],
        candidates=[
            ClipCandidate(
                asset_path=video,
                start_s=0,
                end_s=6,
                quality_score=0.9,
                motion_score=0.2,
                diversity_key="clip:0",
            )
        ],
        audio=AudioAnalysis(path=None, duration_s=0, beats_s=[], energy=[]),
    )

    deps = PipelineDependencies(
        analyze=lambda input_path, music_path: report,
        render=lambda timeline, output_path, music_path: None,
        export_resolve=lambda timeline, out_path: None,
    )
    pipeline = CutPipeline(dependencies=deps)

    result = pipeline.cut(input_dir=input_dir, music_path=None, output_dir=output_dir, dry_run=True)

    assert result.final_video == output_dir / "final.mp4"
    assert (output_dir / "analysis.json").exists()
    assert (output_dir / "cut-plan.json").exists()
    assert (output_dir / "timeline.json").exists()


def test_pipeline_emits_progress_events_for_dry_run(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    video = input_dir / "clip.mp4"
    video.write_text("", encoding="utf-8")
    events: list[ProgressEvent] = []

    report = AnalysisReport(
        media=[MediaAsset(path=video, duration_s=8, width=1920, height=1080, fps=25)],
        candidates=[
            ClipCandidate(
                asset_path=video,
                start_s=0,
                end_s=6,
                quality_score=0.9,
                motion_score=0.2,
                diversity_key="clip:0",
            )
        ],
        audio=AudioAnalysis(path=None, duration_s=0, beats_s=[], energy=[]),
    )
    deps = PipelineDependencies(
        analyze=lambda input_path, music_path: report,
        render=lambda timeline, output_path, music_path: None,
        export_resolve=lambda timeline, out_path: None,
    )

    CutPipeline(dependencies=deps).cut(
        input_dir=input_dir,
        music_path=None,
        output_dir=output_dir,
        dry_run=True,
        progress=events.append,
    )

    assert [event.phase for event in events] == [
        PipelinePhase.ANALYZING_FOOTAGE,
        PipelinePhase.PLANNING_CUT,
        PipelinePhase.EXPORTING_RESOLVE_HANDOFF,
        PipelinePhase.DONE,
    ]


def test_pipeline_emits_render_progress_when_rendering(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    video = input_dir / "clip.mp4"
    video.write_text("", encoding="utf-8")
    events: list[ProgressEvent] = []

    report = AnalysisReport(
        media=[MediaAsset(path=video, duration_s=8, width=1920, height=1080, fps=25)],
        candidates=[
            ClipCandidate(
                asset_path=video,
                start_s=0,
                end_s=6,
                quality_score=0.9,
                motion_score=0.2,
                diversity_key="clip:0",
            )
        ],
        audio=AudioAnalysis(path=None, duration_s=0, beats_s=[], energy=[]),
    )
    deps = PipelineDependencies(
        analyze=lambda input_path, music_path: report,
        render=lambda timeline, output_path, music_path: None,
        export_resolve=lambda timeline, out_path: None,
    )

    CutPipeline(dependencies=deps).cut(
        input_dir=input_dir,
        music_path=None,
        output_dir=output_dir,
        dry_run=False,
        progress=events.append,
    )

    assert [event.phase for event in events] == [
        PipelinePhase.ANALYZING_FOOTAGE,
        PipelinePhase.PLANNING_CUT,
        PipelinePhase.EXPORTING_RESOLVE_HANDOFF,
        PipelinePhase.RENDERING_FINAL_VIDEO,
        PipelinePhase.DONE,
    ]


def test_default_analyze_builds_candidates_across_long_assets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    video = input_dir / "clip.mp4"
    video.write_text("", encoding="utf-8")

    monkeypatch.setattr("aicutting.pipeline.discover_videos", lambda _: [video])
    monkeypatch.setattr("aicutting.pipeline.discover_music", lambda _: None)
    monkeypatch.setattr(
        "aicutting.pipeline.probe_video",
        lambda _: MediaAsset(path=video, duration_s=72.0, width=3840, height=2160, fps=60.0),
    )
    monkeypatch.setattr(
        "aicutting.pipeline.analyze_music",
        lambda _: AudioAnalysis(path=None, duration_s=0.0, beats_s=[], energy=[]),
    )

    report = default_analyze(input_dir, music_path=None)

    assert len(report.candidates) >= 10
    assert report.candidates[0].start_s > 0.0
    assert any(candidate.start_s >= 30.0 for candidate in report.candidates)


def test_pipeline_writes_director_artifacts(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    video = input_dir / "clip.mp4"
    video.write_text("", encoding="utf-8")

    report = AnalysisReport(
        media=[MediaAsset(path=video, duration_s=8, width=1920, height=1080, fps=25)],
        candidates=[
            ClipCandidate(
                asset_path=video,
                start_s=0,
                end_s=5,
                quality_score=0.9,
                motion_score=0.2,
                diversity_key="clip:0",
            )
        ],
        audio=AudioAnalysis(path=None, duration_s=0, beats_s=[], energy=[]),
    )
    deps = PipelineDependencies(
        analyze=lambda input_path, music_path: report,
        render=lambda timeline, output_path, music_path: None,
        export_resolve=lambda timeline, out_path: None,
    )

    CutPipeline(dependencies=deps).cut(
        input_dir=input_dir,
        music_path=None,
        output_dir=output_dir,
        dry_run=True,
    )

    assert (output_dir / "director-report.json").exists()
    assert (output_dir / "rejected-segments.json").exists()
    assert (output_dir / "location-suggestions.json").exists()


def test_pipeline_writes_high_confidence_agent_location_to_timeline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    video = input_dir / "clip.mp4"
    video.write_text("", encoding="utf-8")
    keyframe = tmp_path / "frame.jpg"
    keyframe.write_bytes(b"fake jpg")

    report = AnalysisReport(
        media=[MediaAsset(path=video, duration_s=8, width=1920, height=1080, fps=25)],
        candidates=[
            ClipCandidate(
                asset_path=video,
                start_s=0,
                end_s=5,
                quality_score=0.9,
                motion_score=0.2,
                diversity_key="clip:0",
            )
        ],
        audio=AudioAnalysis(path=None, duration_s=0, beats_s=[], energy=[]),
    )
    deps = PipelineDependencies(
        analyze=lambda input_path, music_path: report,
        render=lambda timeline, output_path, music_path: None,
        export_resolve=lambda timeline, out_path: None,
    )
    monkeypatch.setattr(
        "aicutting.pipeline.extract_location_keyframes",
        lambda candidates, output_dir: [keyframe],
    )
    monkeypatch.setattr(
        "aicutting.pipeline.detect_agent_backends",
        lambda: [AgentBackend(name="codex", executable="codex", available=True)],
    )
    monkeypatch.setattr(
        "aicutting.pipeline.resolve_location_suggestions",
        lambda images, backends, workdir: [
            LocationSuggestion(
                title="Madeira Coast",
                place="Madeira, Portugal",
                confidence=0.88,
                evidence=["agent matched cliffs and terraced coastline"],
                should_render=True,
            )
        ],
    )

    CutPipeline(dependencies=deps).cut(
        input_dir=input_dir,
        music_path=None,
        output_dir=output_dir,
        dry_run=True,
    )

    timeline = json.loads((output_dir / "timeline.json").read_text(encoding="utf-8"))
    suggestions = json.loads(
        (output_dir / "location-suggestions.json").read_text(encoding="utf-8")
    )

    assert timeline["title"]["title"] == "Madeira Coast"
    assert timeline["title"]["subtitle"] == "Madeira, Portugal"
    assert suggestions[0]["title"] == "Madeira Coast"


def test_pipeline_writes_drone_director_3_artifacts_with_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    video = input_dir / "clip.mp4"
    video.write_text("", encoding="utf-8")
    report = AnalysisReport(
        media=[MediaAsset(path=video, duration_s=60, width=1920, height=1080, fps=25)],
        candidates=[
            ClipCandidate(
                asset_path=video, start_s=20, end_s=25, quality_score=0.9, motion_score=0.7,
                diversity_key="c0", shot_type=DroneShotType.REVEAL, drone_director_score=0.9,
            ),
            ClipCandidate(
                asset_path=video, start_s=30, end_s=35, quality_score=0.85, motion_score=0.6,
                diversity_key="c1", shot_type=DroneShotType.APPROACH, drone_director_score=0.85,
            ),
            ClipCandidate(
                asset_path=video, start_s=40, end_s=45, quality_score=0.8, motion_score=0.5,
                diversity_key="c2", shot_type=DroneShotType.ESTABLISHING, drone_director_score=0.8,
            ),
        ],
        audio=AudioAnalysis(
            path=None, duration_s=12.0, beats_s=[0, 1, 2, 3, 4, 5, 6, 7, 8], energy=[0.2, 0.9]
        ),
    )
    # No agent on PATH -> deterministic fallback editor.
    monkeypatch.setattr("aicutting.pipeline.detect_agent_backends", lambda: [])
    deps = PipelineDependencies(
        analyze=lambda input_path, music_path: report,
        render=lambda timeline, output_path, music_path: None,
        export_resolve=lambda timeline, out_path: None,
    )

    CutPipeline(dependencies=deps).cut(input_dir, None, output_dir, dry_run=True)

    assert (output_dir / "rhythm-grid.json").exists()
    assert (output_dir / "footage-ratings.json").exists()
    assert (output_dir / "edit-decision.json").exists()
    assert (output_dir / "director-3-report.json").exists()
    plan = json.loads((output_dir / "cut-plan.json").read_text(encoding="utf-8"))
    assert plan["style"] == "ai_drone_director_30"
    assert len(plan["timeline"]["clips"]) >= 1


def test_compose_title_combines_place_and_date() -> None:
    location = LocationTitle(title="Iceland", subtitle="Iceland", confidence=0.7)
    title = _compose_title(location, "June 2025")
    assert title is not None
    assert title.title == "Iceland"  # where
    assert title.subtitle == "June 2025"  # when


def test_compose_title_falls_back_to_date_only() -> None:
    title = _compose_title(None, "June 2025")
    assert title is not None and title.title == "June 2025"


def test_compose_title_none_without_place_or_date() -> None:
    assert _compose_title(None, None) is None
