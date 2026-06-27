import io

from rich.console import Console

from aicutting.core.progress import PipelinePhase, ProgressEvent
from aicutting.tui import RunReporter


def _render(reporter: RunReporter) -> str:
    console = Console(file=io.StringIO(), force_terminal=False, width=120)
    console.print(reporter.render())
    return console.file.getvalue()  # type: ignore[attr-defined]


def test_run_reporter_shows_stages_and_detail() -> None:
    reporter = RunReporter()
    reporter.handle(ProgressEvent(phase=PipelinePhase.ANALYZING_FOOTAGE, message="3 videos"))
    reporter.handle(
        ProgressEvent(phase=PipelinePhase.RATING_FOOTAGE, message="96 moments", step=3, total=8)
    )

    out = _render(reporter)
    assert "Analyzing footage" in out
    assert "3 videos" in out
    assert "Rating footage" in out
    assert "96 moments" in out
    assert "3/8" in out


def test_run_reporter_marks_done() -> None:
    reporter = RunReporter()
    reporter.handle(ProgressEvent(phase=PipelinePhase.ANALYZING_FOOTAGE))
    reporter.handle(ProgressEvent(phase=PipelinePhase.DONE, message="42 clips"))

    assert _render(reporter).lower().count("done") >= 1
