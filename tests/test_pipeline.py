from pathlib import Path

from aicutting.core.models import AnalysisReport, AudioAnalysis, ClipCandidate, MediaAsset
from aicutting.core.progress import PipelinePhase, ProgressEvent
from aicutting.pipeline import CutPipeline, PipelineDependencies


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

    assert PipelinePhase.RENDERING_FINAL_VIDEO in [event.phase for event in events]
