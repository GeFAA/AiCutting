# AiCutting Desktop Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first professional AiCutting Studio desktop frontend so non-technical users can select videos, optional music, an output folder, run the existing pipeline, watch progress, and open the result.

**Architecture:** Add a PySide6/Qt GUI under `aicutting.gui` while keeping the existing CLI and `CutPipeline` as the source of truth. Most behavior is tested without Qt through state, validation, progress, and job-runner modules; Qt code becomes a thin presentation layer over those stable units.

**Tech Stack:** Python 3.11+, PySide6 as an optional GUI dependency, Typer CLI entrypoint, pytest, Ruff, mypy, existing FFmpeg/Resolve pipeline modules.

---

## Scope Check

The approved design is focused enough for one implementation plan. It has one primary subsystem, the desktop frontend, with two small supporting changes: pipeline progress events and GUI-safe job orchestration. Packaging a Windows installer remains outside this plan.

## File Structure

- `src/aicutting/core/progress.py`: shared progress phases, events, callbacks, and cooperative cancellation primitive.
- `src/aicutting/pipeline.py`: accept optional progress callbacks and emit coarse phases while preserving existing CLI behavior.
- `src/aicutting/gui/__init__.py`: GUI package marker.
- `src/aicutting/gui/state.py`: GUI selections, job status, preset names, validation result, and path validation helpers that do not import Qt.
- `src/aicutting/gui/jobs.py`: Qt-free job request/result wrapper around `CutPipeline`.
- `src/aicutting/gui/qt.py`: lazy PySide6 import helper with a friendly install error.
- `src/aicutting/gui/app.py`: `aicutting-studio` entrypoint and Qt application bootstrap.
- `src/aicutting/gui/worker.py`: PySide6 worker object that runs the job on a background thread and emits signals.
- `src/aicutting/gui/widgets.py`: small Qt widgets for path picking, status, logs, and results.
- `src/aicutting/gui/main_window.py`: guided one-window AiCutting Studio UI composition and event wiring.
- `src/aicutting/cli.py`: add `aicutting gui` command without importing PySide6 at module import time.
- `pyproject.toml`: add optional `gui` dependency and `aicutting-studio` script.
- `README.md`: document how to install and launch the GUI.
- `docs/architecture.md`: add the GUI boundary and progress callback rule.
- `tests/core/test_progress.py`: progress primitives.
- `tests/test_pipeline.py`: pipeline progress callback behavior.
- `tests/gui/test_state.py`: GUI validation and state transitions.
- `tests/gui/test_jobs.py`: job runner success/failure without Qt.
- `tests/gui/test_app_entrypoint.py`: lazy GUI entrypoint behavior.
- `tests/gui/test_qt_smoke.py`: optional PySide6 smoke tests skipped when PySide6 is unavailable.
- `tests/test_cli.py`: CLI remains stable and `gui` command delegates lazily.

---

### Task 1: Add Shared Progress Primitives

**Files:**
- Create: `src/aicutting/core/progress.py`
- Test: `tests/core/test_progress.py`

- [ ] **Step 1: Write the failing progress primitive tests**

Create `tests/core/test_progress.py`:

```python
from aicutting.core.progress import (
    CancellationToken,
    PipelineCancelledError,
    PipelinePhase,
    ProgressEvent,
    emit_progress,
)


def test_progress_event_defaults_to_phase_label() -> None:
    event = ProgressEvent(phase=PipelinePhase.CHECKING_INPUTS)

    assert event.message == "Checking inputs"
    assert event.step is None
    assert event.total is None


def test_emit_progress_calls_callback_with_event() -> None:
    events: list[ProgressEvent] = []

    emit_progress(
        events.append,
        PipelinePhase.RENDERING_FINAL_VIDEO,
        "Rendering final video",
        step=6,
        total=7,
    )

    assert events == [
        ProgressEvent(
            phase=PipelinePhase.RENDERING_FINAL_VIDEO,
            message="Rendering final video",
            step=6,
            total=7,
        )
    ]


def test_cancelled_token_raises_pipeline_cancelled_error() -> None:
    token = CancellationToken()
    token.cancel()

    try:
        token.raise_if_cancelled()
    except PipelineCancelledError as exc:
        assert str(exc) == "Cut was cancelled by the user."
    else:
        raise AssertionError("Expected PipelineCancelledError")
```

- [ ] **Step 2: Run the failing tests**

Run:

```powershell
py -m pytest tests/core/test_progress.py -q
```

Expected: FAIL because `aicutting.core.progress` does not exist.

- [ ] **Step 3: Implement progress primitives**

Create `src/aicutting/core/progress.py`:

```python
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from aicutting.core.errors import AiCuttingError


class PipelinePhase(StrEnum):
    CHECKING_INPUTS = "checking_inputs"
    FINDING_VIDEOS = "finding_videos"
    ANALYZING_FOOTAGE = "analyzing_footage"
    ANALYZING_MUSIC = "analyzing_music"
    PLANNING_CUT = "planning_cut"
    EXPORTING_RESOLVE_HANDOFF = "exporting_resolve_handoff"
    RENDERING_FINAL_VIDEO = "rendering_final_video"
    DONE = "done"


PHASE_LABELS: dict[PipelinePhase, str] = {
    PipelinePhase.CHECKING_INPUTS: "Checking inputs",
    PipelinePhase.FINDING_VIDEOS: "Finding videos",
    PipelinePhase.ANALYZING_FOOTAGE: "Analyzing footage",
    PipelinePhase.ANALYZING_MUSIC: "Analyzing music",
    PipelinePhase.PLANNING_CUT: "Planning cut",
    PipelinePhase.EXPORTING_RESOLVE_HANDOFF: "Exporting Resolve handoff",
    PipelinePhase.RENDERING_FINAL_VIDEO: "Rendering final video",
    PipelinePhase.DONE: "Done",
}


class PipelineCancelledError(AiCuttingError):
    pass


@dataclass(frozen=True)
class ProgressEvent:
    phase: PipelinePhase
    message: str | None = None
    step: int | None = None
    total: int | None = None

    def __post_init__(self) -> None:
        if self.message is None:
            object.__setattr__(self, "message", PHASE_LABELS[self.phase])


ProgressCallback = Callable[[ProgressEvent], None]


class CancellationToken:
    def __init__(self) -> None:
        self._cancelled = False

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True

    def raise_if_cancelled(self) -> None:
        if self._cancelled:
            raise PipelineCancelledError("Cut was cancelled by the user.")


def emit_progress(
    callback: ProgressCallback | None,
    phase: PipelinePhase,
    message: str | None = None,
    step: int | None = None,
    total: int | None = None,
) -> None:
    if callback is not None:
        callback(ProgressEvent(phase=phase, message=message, step=step, total=total))
```

- [ ] **Step 4: Verify progress tests pass**

Run:

```powershell
py -m pytest tests/core/test_progress.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit progress primitives**

Run:

```powershell
git add src/aicutting/core/progress.py tests/core/test_progress.py
git commit -m "feat: add pipeline progress primitives"
```

---

### Task 2: Emit Pipeline Progress Without Regressing CLI

**Files:**
- Modify: `src/aicutting/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Add failing pipeline progress tests**

Append to `tests/test_pipeline.py`:

```python
from aicutting.core.progress import PipelinePhase, ProgressEvent


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
```

- [ ] **Step 2: Run failing pipeline progress tests**

Run:

```powershell
py -m pytest tests/test_pipeline.py -q
```

Expected: FAIL because `CutPipeline.cut` does not accept `progress`.

- [ ] **Step 3: Add progress emission to the pipeline**

Modify `src/aicutting/pipeline.py`:

```python
from aicutting.core.progress import ProgressCallback, PipelinePhase, emit_progress
```

Update the `cut` signature and body:

```python
    def cut(
        self,
        input_dir: Path,
        music_path: Path | None,
        output_dir: Path,
        dry_run: bool,
        progress: ProgressCallback | None = None,
    ) -> PipelineResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        emit_progress(progress, PipelinePhase.ANALYZING_FOOTAGE, step=1, total=4)
        report = self.dependencies.analyze(input_dir, music_path)

        emit_progress(progress, PipelinePhase.PLANNING_CUT, step=2, total=4)
        plan = build_cut_plan(report)
        final_video = output_dir / "final.mp4"

        write_json_model(output_dir / "analysis.json", report)
        write_json_model(output_dir / "cut-plan.json", plan)
        write_json_model(output_dir / "timeline.json", plan.timeline)

        emit_progress(progress, PipelinePhase.EXPORTING_RESOLVE_HANDOFF, step=3, total=4)
        self.dependencies.export_resolve(plan.timeline, output_dir)
        if not dry_run:
            emit_progress(progress, PipelinePhase.RENDERING_FINAL_VIDEO, step=4, total=4)
            self.dependencies.render(plan.timeline, final_video, report.audio.path)

        emit_progress(progress, PipelinePhase.DONE)
        return PipelineResult(
            analysis=output_dir / "analysis.json",
            cut_plan=output_dir / "cut-plan.json",
            timeline=output_dir / "timeline.json",
            final_video=final_video,
            output_dir=output_dir,
        )
```

- [ ] **Step 4: Verify existing CLI tests still pass**

Run:

```powershell
py -m pytest tests/test_pipeline.py tests/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit pipeline progress support**

Run:

```powershell
git add src/aicutting/pipeline.py tests/test_pipeline.py
git commit -m "feat: report pipeline progress"
```

---

### Task 3: Add GUI State and Validation Helpers

**Files:**
- Create: `src/aicutting/gui/__init__.py`
- Create: `src/aicutting/gui/state.py`
- Test: `tests/gui/test_state.py`

- [ ] **Step 1: Write failing GUI state tests**

Create `tests/gui/test_state.py`:

```python
from pathlib import Path

from aicutting.gui.state import (
    GuiSelection,
    JobStatus,
    Preset,
    default_output_dir,
    validate_selection,
)


def test_default_output_dir_is_inside_source_parent(tmp_path: Path) -> None:
    source = tmp_path / "drone"
    source.mkdir()

    assert default_output_dir(source) == tmp_path / "drone-aicutting-output"


def test_selection_with_video_folder_and_output_is_ready(tmp_path: Path) -> None:
    source = tmp_path / "drone"
    source.mkdir()
    (source / "clip.mp4").write_text("", encoding="utf-8")
    output = tmp_path / "out"
    selection = GuiSelection(input_dir=source, music_path=None, output_dir=output)

    result = validate_selection(selection)

    assert result.ready is True
    assert result.status == JobStatus.READY
    assert result.messages == []


def test_selection_rejects_folder_without_supported_videos(tmp_path: Path) -> None:
    source = tmp_path / "empty"
    source.mkdir()
    output = tmp_path / "out"

    result = validate_selection(GuiSelection(input_dir=source, output_dir=output))

    assert result.ready is False
    assert result.status == JobStatus.IDLE
    assert "No supported video files found" in result.messages[0]


def test_selection_accepts_supported_music_file(tmp_path: Path) -> None:
    source = tmp_path / "drone"
    source.mkdir()
    (source / "clip.mov").write_text("", encoding="utf-8")
    music = tmp_path / "song.mp3"
    music.write_text("", encoding="utf-8")

    result = validate_selection(
        GuiSelection(
            input_dir=source,
            music_path=music,
            output_dir=tmp_path / "out",
            preset=Preset.CINEMATIC_AUTO,
        )
    )

    assert result.ready is True
```

- [ ] **Step 2: Run failing GUI state tests**

Run:

```powershell
py -m pytest tests/gui/test_state.py -q
```

Expected: FAIL because `aicutting.gui.state` does not exist.

- [ ] **Step 3: Implement GUI state module**

Create `src/aicutting/gui/__init__.py`:

```python
"""Desktop GUI support for AiCutting Studio."""
```

Create `src/aicutting/gui/state.py`:

```python
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from aicutting.analysis.discovery import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS


class JobStatus(StrEnum):
    IDLE = "idle"
    READY = "ready"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCEL_REQUESTED = "cancel_requested"


class Preset(StrEnum):
    CINEMATIC_AUTO = "cinematic_auto"

    @property
    def label(self) -> str:
        return "Cinematic Auto"


@dataclass(frozen=True)
class GuiSelection:
    input_dir: Path | None = None
    music_path: Path | None = None
    output_dir: Path | None = None
    preset: Preset = Preset.CINEMATIC_AUTO
    dry_run: bool = False


@dataclass(frozen=True)
class ValidationResult:
    status: JobStatus
    messages: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return self.status == JobStatus.READY


def default_output_dir(input_dir: Path) -> Path:
    return input_dir.parent / f"{input_dir.name}-aicutting-output"


def validate_selection(selection: GuiSelection) -> ValidationResult:
    messages: list[str] = []
    if selection.input_dir is None:
        messages.append("Choose a folder with drone videos.")
    elif not selection.input_dir.exists():
        messages.append(f"Input folder does not exist: {selection.input_dir}")
    elif not selection.input_dir.is_dir():
        messages.append(f"Input path must be a folder: {selection.input_dir}")
    elif not any(
        path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
        for path in selection.input_dir.iterdir()
    ):
        messages.append(f"No supported video files found in {selection.input_dir}")

    if selection.music_path is not None:
        if not selection.music_path.exists():
            messages.append(f"Music path does not exist: {selection.music_path}")
        elif selection.music_path.is_file() and selection.music_path.suffix.lower() not in AUDIO_EXTENSIONS:
            messages.append(f"Unsupported music file: {selection.music_path}")
        elif selection.music_path.is_dir() and not any(
            path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
            for path in selection.music_path.iterdir()
        ):
            messages.append(f"No supported music file found at {selection.music_path}")

    if selection.output_dir is None:
        messages.append("Choose an output folder.")

    return ValidationResult(
        status=JobStatus.READY if not messages else JobStatus.IDLE,
        messages=messages,
    )
```

- [ ] **Step 4: Verify GUI state tests pass**

Run:

```powershell
py -m pytest tests/gui/test_state.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit GUI state helpers**

Run:

```powershell
git add src/aicutting/gui/__init__.py src/aicutting/gui/state.py tests/gui/test_state.py
git commit -m "feat: add desktop gui state"
```

---

### Task 4: Add Qt-Free GUI Job Runner

**Files:**
- Create: `src/aicutting/gui/jobs.py`
- Test: `tests/gui/test_jobs.py`

- [ ] **Step 1: Write failing job runner tests**

Create `tests/gui/test_jobs.py`:

```python
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
        def cut(self, input_dir, music_path, output_dir, dry_run, progress=None):
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


def test_run_cut_job_returns_failure_for_aicutting_error(tmp_path: Path) -> None:
    class FailingPipeline:
        def cut(self, input_dir, music_path, output_dir, dry_run, progress=None):
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
        def cut(self, input_dir, music_path, output_dir, dry_run, progress=None):
            del input_dir, music_path, output_dir, dry_run, progress
            raise RuntimeError("render process crashed")

    result = run_cut_job(
        JobRequest(input_dir=tmp_path, music_path=None, output_dir=tmp_path / "out"),
        pipeline_factory=FailingPipeline,
    )

    assert isinstance(result, JobFailure)
    assert result.message == "render process crashed"
    assert result.error_type == "RuntimeError"
```

- [ ] **Step 2: Run failing job runner tests**

Run:

```powershell
py -m pytest tests/gui/test_jobs.py -q
```

Expected: FAIL because `aicutting.gui.jobs` does not exist.

- [ ] **Step 3: Implement job runner**

Create `src/aicutting/gui/jobs.py`:

```python
from dataclasses import dataclass
from pathlib import Path

from aicutting.core.errors import AiCuttingError
from aicutting.core.progress import ProgressCallback
from aicutting.pipeline import CutPipeline, PipelineResult


@dataclass(frozen=True)
class JobRequest:
    input_dir: Path
    music_path: Path | None
    output_dir: Path
    dry_run: bool = False


@dataclass(frozen=True)
class JobSuccess:
    result: PipelineResult


@dataclass(frozen=True)
class JobFailure:
    message: str
    error_type: str


JobResult = JobSuccess | JobFailure


def run_cut_job(
    request: JobRequest,
    pipeline_factory: type[CutPipeline] = CutPipeline,
    progress: ProgressCallback | None = None,
) -> JobResult:
    try:
        result = pipeline_factory().cut(
            input_dir=request.input_dir,
            music_path=request.music_path,
            output_dir=request.output_dir,
            dry_run=request.dry_run,
            progress=progress,
        )
    except AiCuttingError as exc:
        return JobFailure(message=str(exc), error_type=type(exc).__name__)
    except Exception as exc:
        return JobFailure(message=str(exc), error_type=type(exc).__name__)
    return JobSuccess(result=result)
```

- [ ] **Step 4: Verify job runner tests pass**

Run:

```powershell
py -m pytest tests/gui/test_jobs.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit job runner**

Run:

```powershell
git add src/aicutting/gui/jobs.py tests/gui/test_jobs.py
git commit -m "feat: add desktop job runner"
```

---

### Task 5: Add Lazy GUI Entrypoints

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/aicutting/cli.py`
- Create: `src/aicutting/gui/qt.py`
- Create: `src/aicutting/gui/app.py`
- Test: `tests/gui/test_app_entrypoint.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing entrypoint tests**

Create `tests/gui/test_app_entrypoint.py`:

```python
import builtins

import pytest

from aicutting.gui.qt import require_qt


def test_require_qt_raises_friendly_error_when_pyside6_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("PySide6"):
            raise ModuleNotFoundError("No module named 'PySide6'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError, match="Install the GUI extra"):
        require_qt()
```

Append to `tests/test_cli.py`:

```python
def test_gui_command_delegates_to_gui_app(monkeypatch) -> None:
    called = False

    def fake_main() -> int:
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr("aicutting.gui.app.main", fake_main)

    result = CliRunner().invoke(app, ["gui"])

    assert result.exit_code == 0
    assert called is True
```

- [ ] **Step 2: Run failing entrypoint tests**

Run:

```powershell
py -m pytest tests/gui/test_app_entrypoint.py tests/test_cli.py -q
```

Expected: FAIL because `aicutting.gui.qt`, `aicutting.gui.app`, and `aicutting gui` are not implemented.

- [ ] **Step 3: Add optional dependency and script**

Modify `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
  "pytest>=8.3",
  "pytest-cov>=5.0",
  "ruff>=0.6.8",
  "mypy>=1.11",
]
gui = [
  "PySide6>=6.8",
]

[project.scripts]
aicutting = "aicutting.cli:app"
aicutting-studio = "aicutting.gui.app:main"

[[tool.mypy.overrides]]
module = [
  "aicutting.gui.app",
  "aicutting.gui.main_window",
  "aicutting.gui.qt",
  "aicutting.gui.widgets",
  "aicutting.gui.worker",
]
ignore_errors = true
```

This keeps optional PySide6 presentation modules from breaking `py -m mypy src`
when the GUI extra is not installed. The GUI modules that hold business logic,
`aicutting.gui.state` and `aicutting.gui.jobs`, remain type-checked.

- [ ] **Step 4: Implement lazy Qt loader and app bootstrap**

Create `src/aicutting/gui/qt.py`:

```python
from dataclasses import dataclass
from types import ModuleType


@dataclass(frozen=True)
class QtModules:
    core: ModuleType
    gui: ModuleType
    widgets: ModuleType


def require_qt() -> QtModules:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "AiCutting Studio requires PySide6. Install the GUI extra with: "
            'py -m pip install -e ".[gui]"'
        ) from exc
    return QtModules(core=QtCore, gui=QtGui, widgets=QtWidgets)
```

Create `src/aicutting/gui/app.py`:

```python
import sys

from aicutting.gui.qt import require_qt


def main() -> int:
    qt = require_qt()
    from aicutting.gui.main_window import MainWindow

    app = qt.widgets.QApplication.instance() or qt.widgets.QApplication(sys.argv)
    app.setApplicationName("AiCutting Studio")
    window = MainWindow()
    window.resize(1100, 720)
    window.show()
    return int(app.exec())
```

- [ ] **Step 5: Add CLI GUI command with friendly failure**

Modify `src/aicutting/cli.py`:

```python
@app.command()
def gui() -> None:
    """Launch AiCutting Studio."""
    try:
        from aicutting.gui.app import main as run_gui

        raise typer.Exit(code=run_gui())
    except RuntimeError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=2) from exc
```

- [ ] **Step 6: Verify entrypoint tests pass**

Run:

```powershell
py -m pytest tests/gui/test_app_entrypoint.py tests/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit lazy GUI entrypoints**

Run:

```powershell
git add pyproject.toml src/aicutting/cli.py src/aicutting/gui/qt.py src/aicutting/gui/app.py tests/gui/test_app_entrypoint.py tests/test_cli.py
git commit -m "feat: add desktop gui entrypoints"
```

---

### Task 6: Build Reusable Qt Widgets

**Files:**
- Create: `src/aicutting/gui/widgets.py`
- Test: `tests/gui/test_qt_smoke.py`

- [ ] **Step 1: Write optional Qt widget smoke tests**

Create `tests/gui/test_qt_smoke.py`:

```python
import pytest


QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from aicutting.gui.widgets import PathPicker, StatusPanel


def test_path_picker_constructs(qtbot) -> None:
    picker = PathPicker(label="Video folder", button_text="Choose")
    qtbot.addWidget(picker)

    assert picker.path() is None
    assert picker.label_text == "Video folder"


def test_status_panel_updates_message(qtbot) -> None:
    panel = StatusPanel()
    qtbot.addWidget(panel)

    panel.set_status("Analyzing footage")

    assert panel.current_message == "Analyzing footage"
```

Add `pytest-qt>=4.4` to the `gui` optional dependency group in `pyproject.toml`:

```toml
gui = [
  "PySide6>=6.8",
  "pytest-qt>=4.4",
]
```

- [ ] **Step 2: Run the optional Qt smoke tests**

Run:

```powershell
py -m pytest tests/gui/test_qt_smoke.py -q
```

Expected on machines without PySide6: SKIPPED. Expected after installing `.[gui]`: FAIL because widgets do not exist.

- [ ] **Step 3: Implement widgets**

Create `src/aicutting/gui/widgets.py`:

```python
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


class PathPicker(QWidget):
    path_changed = Signal(object)

    def __init__(self, label: str, button_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.label_text = label
        self._path: Path | None = None

        self.label = QLabel(label)
        self.input = QLineEdit()
        self.input.setReadOnly(True)
        self.button = QPushButton(button_text)

        layout = QHBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.input, 1)
        layout.addWidget(self.button)

    def set_path(self, path: Path | None) -> None:
        self._path = path
        self.input.setText("" if path is None else str(path))
        self.path_changed.emit(path)

    def path(self) -> Path | None:
        return self._path


class StatusPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_message = "Ready"
        self.message_label = QLabel(self.current_message)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)

        layout = QVBoxLayout(self)
        layout.addWidget(self.message_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.log)

    def set_status(self, message: str, busy: bool = False) -> None:
        self.current_message = message
        self.message_label.setText(message)
        self.progress.setVisible(busy)

    def append_log(self, line: str) -> None:
        self.log.appendPlainText(line)
```

- [ ] **Step 4: Verify widget smoke behavior**

Run:

```powershell
py -m pytest tests/gui/test_qt_smoke.py -q
```

Expected on machines without PySide6: SKIPPED. Expected after installing `.[gui]`: PASS.

- [ ] **Step 5: Commit reusable widgets**

Run:

```powershell
git add pyproject.toml src/aicutting/gui/widgets.py tests/gui/test_qt_smoke.py
git commit -m "feat: add desktop gui widgets"
```

---

### Task 7: Add Qt Worker and Main Window

**Files:**
- Create: `src/aicutting/gui/worker.py`
- Create: `src/aicutting/gui/main_window.py`
- Modify: `tests/gui/test_qt_smoke.py`

- [ ] **Step 1: Extend optional smoke tests for the main window**

Append to `tests/gui/test_qt_smoke.py`:

```python
from aicutting.gui.main_window import MainWindow


def test_main_window_constructs(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "AiCutting Studio"
    assert window.start_button.isEnabled() is False
```

- [ ] **Step 2: Run the optional main window smoke test**

Run:

```powershell
py -m pytest tests/gui/test_qt_smoke.py -q
```

Expected on machines without PySide6: SKIPPED. Expected after installing `.[gui]`: FAIL because the main window does not exist.

- [ ] **Step 3: Implement Qt worker**

Create `src/aicutting/gui/worker.py`:

```python
from PySide6.QtCore import QObject, Signal, Slot

from aicutting.core.progress import CancellationToken, ProgressEvent
from aicutting.gui.jobs import JobFailure, JobRequest, JobSuccess, run_cut_job


class CutWorker(QObject):
    progress = Signal(object)
    succeeded = Signal(object)
    failed = Signal(object)
    finished = Signal()

    def __init__(self, request: JobRequest, token: CancellationToken | None = None) -> None:
        super().__init__()
        self.request = request
        self.token = token or CancellationToken()

    def cancel(self) -> None:
        self.token.cancel()

    @Slot()
    def run(self) -> None:
        def report(event: ProgressEvent) -> None:
            self.token.raise_if_cancelled()
            self.progress.emit(event)

        result = run_cut_job(self.request, progress=report)
        if isinstance(result, JobSuccess):
            self.succeeded.emit(result.result)
        elif isinstance(result, JobFailure):
            self.failed.emit(result)
        self.finished.emit()
```

- [ ] **Step 4: Implement guided main window**

Create `src/aicutting/gui/main_window.py`:

```python
from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from aicutting.core.progress import ProgressEvent
from aicutting.gui.jobs import JobFailure, JobRequest
from aicutting.gui.state import GuiSelection, JobStatus, default_output_dir, validate_selection
from aicutting.gui.widgets import PathPicker, StatusPanel
from aicutting.gui.worker import CutWorker
from aicutting.pipeline import PipelineResult


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AiCutting Studio")
        self.status = JobStatus.IDLE
        self.thread: QThread | None = None
        self.worker: CutWorker | None = None

        self.video_picker = PathPicker("Video folder", "Choose")
        self.music_picker = PathPicker("Music", "Choose")
        self.output_picker = PathPicker("Output", "Choose")
        self.start_button = QPushButton("Start")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.status_panel = StatusPanel()
        self.result_label = QLabel("")

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addWidget(QLabel("AiCutting Studio"))
        layout.addWidget(self.video_picker)
        layout.addWidget(self.music_picker)
        layout.addWidget(self.output_picker)

        actions = QHBoxLayout()
        actions.addWidget(self.start_button)
        actions.addWidget(self.cancel_button)
        layout.addLayout(actions)
        layout.addWidget(self.status_panel)
        layout.addWidget(self.result_label)
        self.setCentralWidget(root)

        self.video_picker.button.clicked.connect(self.choose_video_folder)
        self.music_picker.button.clicked.connect(self.choose_music)
        self.output_picker.button.clicked.connect(self.choose_output_folder)
        self.start_button.clicked.connect(self.start_job)
        self.cancel_button.clicked.connect(self.cancel_job)

        self.video_picker.path_changed.connect(lambda _: self.refresh_ready_state())
        self.music_picker.path_changed.connect(lambda _: self.refresh_ready_state())
        self.output_picker.path_changed.connect(lambda _: self.refresh_ready_state())
        self.refresh_ready_state()

    def current_selection(self) -> GuiSelection:
        return GuiSelection(
            input_dir=self.video_picker.path(),
            music_path=self.music_picker.path(),
            output_dir=self.output_picker.path(),
        )

    def choose_video_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Choose video folder")
        if selected:
            path = Path(selected)
            self.video_picker.set_path(path)
            if self.output_picker.path() is None:
                self.output_picker.set_path(default_output_dir(path))

    def choose_music(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Choose music",
            "",
            "Audio files (*.wav *.mp3 *.m4a *.aac *.flac)",
        )
        if selected:
            self.music_picker.set_path(Path(selected))

    def choose_output_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if selected:
            self.output_picker.set_path(Path(selected))

    def refresh_ready_state(self) -> None:
        validation = validate_selection(self.current_selection())
        self.status = validation.status
        self.start_button.setEnabled(validation.ready)
        if validation.messages:
            self.status_panel.set_status(validation.messages[0], busy=False)
        else:
            self.status_panel.set_status("Ready", busy=False)

    def start_job(self) -> None:
        validation = validate_selection(self.current_selection())
        if not validation.ready:
            self.refresh_ready_state()
            return

        selection = self.current_selection()
        assert selection.input_dir is not None
        assert selection.output_dir is not None
        request = JobRequest(
            input_dir=selection.input_dir,
            music_path=selection.music_path,
            output_dir=selection.output_dir,
            dry_run=selection.dry_run,
        )

        self.thread = QThread()
        self.worker = CutWorker(request)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.succeeded.connect(self.on_success)
        self.worker.failed.connect(self.on_failure)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.on_worker_finished)

        self.status = JobStatus.RUNNING
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status_panel.set_status("Starting", busy=True)
        self.thread.start()

    def cancel_job(self) -> None:
        self.status = JobStatus.CANCEL_REQUESTED
        self.cancel_button.setEnabled(False)
        self.status_panel.set_status("Stopping after the current step", busy=True)
        if self.worker is not None:
            self.worker.cancel()

    def on_progress(self, event: ProgressEvent) -> None:
        self.status_panel.set_status(event.message or event.phase.value, busy=True)
        self.status_panel.append_log(event.message or event.phase.value)

    def on_success(self, result: PipelineResult) -> None:
        self.status = JobStatus.COMPLETE
        self.status_panel.set_status("Done", busy=False)
        self.result_label.setText(f"Finished video: {result.final_video}")

    def on_failure(self, failure: JobFailure) -> None:
        self.status = JobStatus.FAILED
        self.status_panel.set_status(failure.message, busy=False)
        self.status_panel.append_log(f"{failure.error_type}: {failure.message}")

    def on_worker_finished(self) -> None:
        self.cancel_button.setEnabled(False)
        if self.status in {JobStatus.COMPLETE, JobStatus.FAILED}:
            self.start_button.setEnabled(True)
        self.thread = None
        self.worker = None
```

- [ ] **Step 5: Verify optional smoke test behavior**

Run:

```powershell
py -m pytest tests/gui/test_qt_smoke.py -q
```

Expected on machines without PySide6: SKIPPED. Expected after installing `.[gui]`: PASS.

- [ ] **Step 6: Commit worker and main window**

Run:

```powershell
git add src/aicutting/gui/worker.py src/aicutting/gui/main_window.py tests/gui/test_qt_smoke.py
git commit -m "feat: add desktop main window"
```

---

### Task 8: Document GUI Usage and Run Full Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`

- [ ] **Step 1: Update README with GUI install and launch commands**

Add this section after development install in `README.md`:

```markdown
## Launch AiCutting Studio

The desktop app is optional during development because it depends on PySide6:

```powershell
py -m pip install -e ".[dev,gui]"
aicutting-studio
```

You can also launch it through the CLI:

```powershell
aicutting gui
```

The GUI keeps the same pipeline as the CLI. It collects a video folder, optional
music, and an output folder, then writes the same `final.mp4`, JSON artifacts, and
Resolve handoff files.
```

- [ ] **Step 2: Update architecture docs**

Add this section to `docs/architecture.md`:

```markdown
## Desktop GUI

AiCutting Studio is a native PySide6 desktop frontend over the same pipeline. GUI
modules live under `aicutting.gui` and do not own edit decisions. They collect
local paths, validate readiness, run `CutPipeline` in a background worker, show
progress events, and expose the output artifacts.

Pipeline progress is represented with shared `ProgressEvent` values from
`aicutting.core.progress`. The CLI can ignore these callbacks, while the GUI uses
them for stable user-facing phases.
```

- [ ] **Step 3: Run focused tests**

Run:

```powershell
py -m pytest tests/core/test_progress.py tests/test_pipeline.py tests/gui/test_state.py tests/gui/test_jobs.py tests/gui/test_app_entrypoint.py tests/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 4: Run full quality checks**

Run:

```powershell
py -m pytest -q
py -m ruff check .
py -m mypy src
```

Expected: all pass. `tests/gui/test_qt_smoke.py` may be skipped when PySide6 is not installed.

- [ ] **Step 5: Run GUI launch smoke commands**

Run without GUI extra:

```powershell
aicutting gui
```

Expected: exits with code 2 and prints the friendly PySide6 install message.

Run after installing GUI extra:

```powershell
py -m pip install -e ".[dev,gui]"
aicutting-studio
```

Expected: AiCutting Studio opens with disabled Start button until a valid video folder and output folder are selected.

- [ ] **Step 6: Commit docs and verification updates**

Run:

```powershell
git add README.md docs/architecture.md
git commit -m "docs: document desktop gui"
```

---

## Final Verification

Run:

```powershell
git status --short --branch
py -m pytest -q
py -m ruff check .
py -m mypy src
py -m aicutting version
```

Expected:

- branch is `codex/aicutting-frontend`,
- worktree is clean,
- all non-optional tests pass,
- Ruff reports no issues,
- mypy succeeds,
- version command prints `AiCutting 0.1.0`.

If PySide6 is installed, also run:

```powershell
py -m pytest tests/gui/test_qt_smoke.py -q
aicutting-studio
```

Expected:

- Qt smoke tests pass,
- desktop window opens,
- Start is disabled before valid input selection,
- app closes without crashing.
