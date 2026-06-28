import json
from pathlib import Path

import numpy as np
import pytest

from aicutting.agents.backends import AgentBackend
from aicutting.analysis.motion import analyze_motion_frames
from aicutting.core.models import (
    AnalysisReport,
    AudioAnalysis,
    ClipCandidate,
    DroneShotType,
    LocationTitle,
    MediaAsset,
)
from aicutting.core.progress import PipelinePhase, ProgressEvent
from aicutting.director.edit_models import FootageMoment
from aicutting.director.models import LocationSuggestion
from aicutting.pipeline import (
    CutPipeline,
    PipelineDependencies,
    _compose_title,
    _gate_moments_by_motion,
    default_analyze,
)


def _motion_frame(x_offset: int = 0) -> np.ndarray:
    frame = np.zeros((80, 120, 3), dtype=np.uint8)
    frame[25:55, 35 + x_offset : 85 + x_offset] = 255
    return frame


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


def test_pipeline_emits_progress_events_for_dry_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    video = input_dir / "clip.mp4"
    video.write_text("", encoding="utf-8")
    events: list[ProgressEvent] = []
    monkeypatch.setattr("aicutting.pipeline.detect_agent_backends", lambda: [])

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

    phases = list(dict.fromkeys(event.phase for event in events))
    assert phases == [
        PipelinePhase.ANALYZING_FOOTAGE,
        PipelinePhase.IDENTIFYING_LOCATION,
        PipelinePhase.DESIGNING_EDIT,
        PipelinePhase.ASSEMBLING_CUT,
        PipelinePhase.BUILDING_REPORT,
        PipelinePhase.EXPORTING_RESOLVE_HANDOFF,
        PipelinePhase.DONE,
    ]


def test_pipeline_emits_render_progress_when_rendering(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    video = input_dir / "clip.mp4"
    video.write_text("", encoding="utf-8")
    events: list[ProgressEvent] = []
    monkeypatch.setattr("aicutting.pipeline.detect_agent_backends", lambda: [])

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

    phases = list(dict.fromkeys(event.phase for event in events))
    assert phases == [
        PipelinePhase.ANALYZING_FOOTAGE,
        PipelinePhase.IDENTIFYING_LOCATION,
        PipelinePhase.DESIGNING_EDIT,
        PipelinePhase.ASSEMBLING_CUT,
        PipelinePhase.BUILDING_REPORT,
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


def _vertical_report(video: Path) -> AnalysisReport:
    # A long-enough beat track so the rhythm grid yields several slots (hence real cuts the
    # self-critic can grade), and 4K media so the 9:16 reframe is a visible downscale.
    return AnalysisReport(
        media=[MediaAsset(path=video, duration_s=80, width=3840, height=2160, fps=25)],
        candidates=[
            ClipCandidate(
                asset_path=video, start_s=20, end_s=25, quality_score=0.9, motion_score=0.7,
                diversity_key="c0", shot_type=DroneShotType.REVEAL, drone_director_score=0.9,
            ),
            ClipCandidate(
                asset_path=video, start_s=35, end_s=40, quality_score=0.85, motion_score=0.6,
                diversity_key="c1", shot_type=DroneShotType.APPROACH, drone_director_score=0.85,
            ),
            ClipCandidate(
                asset_path=video, start_s=50, end_s=55, quality_score=0.8, motion_score=0.5,
                diversity_key="c2", shot_type=DroneShotType.ESTABLISHING, drone_director_score=0.8,
            ),
        ],
        audio=AudioAnalysis(
            path=None,
            duration_s=40.0,
            beats_s=[i * 0.5 for i in range(80)],
            energy=[0.2, 0.9, 0.3, 0.8],
        ),
    )


def test_pipeline_writes_self_critic_quality(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    video = input_dir / "clip.mp4"
    video.write_text("", encoding="utf-8")
    monkeypatch.setattr("aicutting.pipeline.detect_agent_backends", lambda: [])
    deps = PipelineDependencies(
        analyze=lambda input_path, music_path: _vertical_report(video),
        render=lambda timeline, output_path, music_path: None,
        export_resolve=lambda timeline, out_path: None,
    )

    CutPipeline(dependencies=deps).cut(input_dir, None, output_dir, dry_run=True)

    quality = json.loads((output_dir / "edit-quality.json").read_text(encoding="utf-8"))
    assert quality["grade"] in {"A", "B", "C", "D", "F"}
    assert 0.0 <= quality["overall"] <= 1.0
    # the cut is laid on beats, so the self-critic should confirm the on-beat dimension
    assert any(dimension["name"] == "on_beat" for dimension in quality["dimensions"])


def test_pipeline_keeps_the_source_master_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    video = input_dir / "clip.mp4"
    video.write_text("", encoding="utf-8")
    monkeypatch.setattr("aicutting.pipeline.detect_agent_backends", lambda: [])
    deps = PipelineDependencies(
        analyze=lambda input_path, music_path: _vertical_report(video),
        render=lambda timeline, output_path, music_path: None,
        export_resolve=lambda timeline, out_path: None,
    )

    CutPipeline(dependencies=deps).cut(input_dir, None, output_dir, dry_run=True)

    timeline = json.loads((output_dir / "timeline.json").read_text(encoding="utf-8"))
    assert (timeline["width"], timeline["height"]) == (3840, 2160)


def test_pipeline_reframes_to_a_vertical_master_for_9_16(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    video = input_dir / "clip.mp4"
    video.write_text("", encoding="utf-8")
    monkeypatch.setattr("aicutting.pipeline.detect_agent_backends", lambda: [])
    deps = PipelineDependencies(
        analyze=lambda input_path, music_path: _vertical_report(video),
        render=lambda timeline, output_path, music_path: None,
        export_resolve=lambda timeline, out_path: None,
    )

    CutPipeline(dependencies=deps).cut(input_dir, None, output_dir, dry_run=True, aspect="9:16")

    timeline = json.loads((output_dir / "timeline.json").read_text(encoding="utf-8"))
    assert (timeline["width"], timeline["height"]) == (1080, 1920)


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


def _scored_moments() -> tuple[list[FootageMoment], dict[str, object]]:
    stable = analyze_motion_frames([_motion_frame(index * 3) for index in range(5)])
    jittery = analyze_motion_frames([_motion_frame(offset) for offset in [0, 16, -10, 22, -6]])
    moments = [
        FootageMoment(moment_id=f"s{i}", asset_path=Path("a.mp4"), timestamp_s=float(i))
        for i in range(5)
    ]
    moments.append(FootageMoment(moment_id="jit", asset_path=Path("a.mp4"), timestamp_s=99.0))
    scores: dict[str, object] = {moment.moment_id: stable for moment in moments[:5]}
    scores["jit"] = jittery
    return moments, scores


def test_gate_moments_by_motion_drops_flagged(monkeypatch: pytest.MonkeyPatch) -> None:
    moments, scores = _scored_moments()
    monkeypatch.setattr("aicutting.pipeline.score_moment_motion", lambda _moments: scores)

    kept = {moment.moment_id for moment in _gate_moments_by_motion(moments)}

    assert "jit" not in kept
    assert kept == {"s0", "s1", "s2", "s3", "s4"}


def test_gate_moments_by_motion_survives_scorer_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    moments = [FootageMoment(moment_id="m1", asset_path=Path("a.mp4"), timestamp_s=1.0)]

    def _boom(_moments: object) -> dict[str, object]:
        raise RuntimeError("cv2 exploded")

    monkeypatch.setattr("aicutting.pipeline.score_moment_motion", _boom)

    assert _gate_moments_by_motion(moments) == moments


def test_gate_moments_by_motion_handles_empty_media() -> None:
    assert _gate_moments_by_motion([]) == []


def test_pipeline_gates_shaky_moments_before_contact_sheets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    video = input_dir / "clip.mp4"
    video.write_text("", encoding="utf-8")

    sampled = [
        FootageMoment(moment_id=f"s{i}", asset_path=video, timestamp_s=float(20 + i))
        for i in range(5)
    ]
    sampled.append(FootageMoment(moment_id="shaky", asset_path=video, timestamp_s=40.0))
    stable = analyze_motion_frames([_motion_frame(index * 3) for index in range(5)])
    jittery = analyze_motion_frames([_motion_frame(offset) for offset in [0, 16, -10, 22, -6]])
    scores = {moment.moment_id: stable for moment in sampled[:5]}
    scores["shaky"] = jittery

    seen: list[list[str]] = []

    def _capture_sheets(moments: list[FootageMoment], _out: Path, **_kwargs: object) -> list:
        seen.append([moment.moment_id for moment in moments])
        return []

    monkeypatch.setattr("aicutting.pipeline.sample_footage_moments", lambda _media: sampled)
    monkeypatch.setattr("aicutting.pipeline.score_moment_motion", lambda _moments: scores)
    monkeypatch.setattr("aicutting.pipeline.build_contact_sheets", _capture_sheets)
    monkeypatch.setattr("aicutting.pipeline.resolve_location_suggestions", lambda *a, **k: [])
    monkeypatch.setattr(
        "aicutting.pipeline.detect_agent_backends",
        lambda: [AgentBackend(name="codex", executable="codex", available=True)],
    )

    report = AnalysisReport(
        media=[MediaAsset(path=video, duration_s=60, width=1920, height=1080, fps=25)],
        candidates=[
            ClipCandidate(
                asset_path=video,
                start_s=20,
                end_s=25,
                quality_score=0.9,
                motion_score=0.4,
                diversity_key="c0",
            )
        ],
        audio=AudioAnalysis(
            path=None, duration_s=12.0, beats_s=[0, 1, 2, 3, 4, 5, 6, 7, 8], energy=[0.2, 0.9]
        ),
    )
    deps = PipelineDependencies(
        analyze=lambda input_path, music_path: report,
        render=lambda timeline, output_path, music_path: None,
        export_resolve=lambda timeline, out_path: None,
    )

    CutPipeline(dependencies=deps).cut(input_dir, None, output_dir, dry_run=True)

    assert seen, "build_contact_sheets was never reached"
    assert "shaky" not in seen[0]
    assert sum(1 for mid in seen[0] if mid.startswith("s")) == 5
