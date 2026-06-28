from pathlib import Path

from aicutting.core.errors import ValidationError
from aicutting.core.progress import PipelinePhase, ProgressEvent
from aicutting.gui.jobs import JobFailure, JobRequest, JobSuccess, run_cut_job
from aicutting.pipeline import PipelineResult


def test_run_cut_job_returns_success(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    (input_dir / "clip.mp4").write_text("", encoding="utf-8")
    events: list[ProgressEvent] = []

    class FakePipeline:
        def cut(self, input_dir, music_path, output_dir, dry_run, progress=None, **kwargs):
            del input_dir, music_path, dry_run
            if progress is not None:
                progress(ProgressEvent(PipelinePhase.DONE))
            output_dir.mkdir()
            return PipelineResult(
                analysis=output_dir / "analysis.json",
                cut_plan=output_dir / "cut-plan.json",
                timeline=output_dir / "timeline.json",
                final_video=output_dir / "final.mp4",
                output_dir=output_dir,
            )

    result = run_cut_job(
        JobRequest(input_dir=input_dir, music_path=None, output_dir=output_dir, dry_run=True),
        pipeline_factory=FakePipeline,
        progress=events.append,
    )

    assert isinstance(result, JobSuccess)
    assert result.result.final_video == output_dir / "final.mp4"
    assert events == [ProgressEvent(PipelinePhase.DONE)]


def test_run_cut_job_accepts_callable_pipeline_factory(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"

    class FakePipeline:
        def cut(self, input_dir, music_path, output_dir, dry_run, progress=None, **kwargs):
            del input_dir, music_path, dry_run, progress
            output_dir.mkdir()
            return PipelineResult(
                analysis=output_dir / "analysis.json",
                cut_plan=output_dir / "cut-plan.json",
                timeline=output_dir / "timeline.json",
                final_video=output_dir / "final.mp4",
                output_dir=output_dir,
            )

    result = run_cut_job(
        JobRequest(input_dir=tmp_path, music_path=None, output_dir=output_dir),
        pipeline_factory=lambda: FakePipeline(),
    )

    assert isinstance(result, JobSuccess)
    assert result.result.output_dir == output_dir


def test_run_cut_job_forwards_style_aspect_and_variants(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    class FakePipeline:
        def cut(self, input_dir, music_path, output_dir, dry_run, progress=None, **kwargs):
            del input_dir, music_path, dry_run, progress
            captured.update(kwargs)
            output_dir.mkdir(parents=True, exist_ok=True)
            return PipelineResult(
                analysis=output_dir / "a.json",
                cut_plan=output_dir / "c.json",
                timeline=output_dir / "t.json",
                final_video=output_dir / "final.mp4",
                output_dir=output_dir,
            )

    result = run_cut_job(
        JobRequest(
            input_dir=tmp_path,
            music_path=None,
            output_dir=tmp_path / "out",
            style="vlog",
            aspect="9:16",
            variants=True,
        ),
        pipeline_factory=lambda: FakePipeline(),
    )

    assert isinstance(result, JobSuccess)
    assert captured["style"].name == "vlog"  # resolved from the string  # type: ignore[union-attr]
    assert captured["aspect"] == "9:16"
    assert captured["variants"] is True


def test_run_cut_job_returns_failure_for_aicutting_error(tmp_path: Path) -> None:
    class FailingPipeline:
        def cut(self, input_dir, music_path, output_dir, dry_run, progress=None, **kwargs):
            del input_dir, music_path, output_dir, dry_run, progress
            raise ValidationError("No supported video files found.")

    result = run_cut_job(
        JobRequest(input_dir=tmp_path, music_path=None, output_dir=tmp_path / "out"),
        pipeline_factory=FailingPipeline,
    )

    assert isinstance(result, JobFailure)
    assert result.message == "No supported video files found."
    assert result.error_type == "ValidationError"


def test_run_cut_job_returns_failure_for_unexpected_error(tmp_path: Path) -> None:
    class FailingPipeline:
        def cut(self, input_dir, music_path, output_dir, dry_run, progress=None, **kwargs):
            del input_dir, music_path, output_dir, dry_run, progress
            raise RuntimeError("render process crashed")

    result = run_cut_job(
        JobRequest(input_dir=tmp_path, music_path=None, output_dir=tmp_path / "out"),
        pipeline_factory=FailingPipeline,
    )

    assert isinstance(result, JobFailure)
    assert result.message == "render process crashed"
    assert result.error_type == "RuntimeError"
