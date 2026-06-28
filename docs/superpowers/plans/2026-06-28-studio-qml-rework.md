# AiCutting Studio QML Rework — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the AiCutting Studio View with an animated PySide6 Qt Quick / QML frontend over the unchanged pipeline, exposing `--style` / `--aspect` / `--variants` and the self-critic grade.

**Architecture:** Keep the entire non-View layer (`pipeline.py`, `core/progress.py`, `gui/jobs.py`, `gui/worker.py`, `gui/state.py`). Add a `Backend(QObject)` that owns the existing `QThread` + `CutWorker`, exposes `Q_PROPERTY`/`Slot`s to QML, and maps the 13 `PipelinePhase` values onto 5 visible stages. Build the View as declarative QML with a `Theme` token singleton. Two additive backend changes: forward style/aspect/variants through `JobRequest`, and surface the critic grade as structured fields on `PipelineResult`.

**Tech Stack:** Python 3.11+, PySide6 (Qt Quick / QML, QtMultimedia), pytest + pytest-qt, ruff, mypy. Spec: `docs/superpowers/specs/2026-06-28-studio-qml-rework-design.md`.

## Global Constraints

- Do NOT change pipeline cut behaviour. The View rework is additive; `py -m pytest`, `py -m ruff check .`, `py -m mypy src` stay green (line-length 100; ruff select E,F,I,UP,B,SIM; mypy strict).
- Keep the working QWidgets app (`gui/main_window.py`, `gui/widgets.py`) running in parallel until QML reaches parity; retire it only in the final task.
- Author every commit as `GeFAA <121340757+GeFAA@users.noreply.github.com>`; never add a `Co-Authored-By: Claude` trailer.
- Colour tokens (verbatim): Canvas `#0B0D10`, Surface-1 `#14171C`, Surface-2 `#1B1F26`, Hairline `#262B33`, Text-hi `#F2F4F7`, Text-mid `#9AA4B2`, Text-low `#5B6675`, Accent `#E8B15A`, Accent-hot `#F4C06B`, Cool `#4FD0C0`, Success `#5BD6A0`, Danger `#E5675B`. Grade ring F→A: `#E5675B → #E8B15A → #5BD6A0`.
- Motion tokens: micro 160ms, control 220ms, scene 450ms; honour a global Reduce Motion flag. Prefer opacity/transform over layout/blur; 60fps budget.
- Style strings resolve via `aicutting.core.style.resolve_style` (cinematic|epic|chill|vlog); aspect strings via `aicutting.render.reframe.resolve_aspect` (16:9|9:16|1:1).

---

## Phase A — Backend foundation (headless, TDD)

### Task 1: Surface the self-critic grade on `PipelineResult`

**Files:**
- Modify: `src/aicutting/pipeline.py` (the `PipelineResult` dataclass ~line 43, and `CutPipeline.cut` return ~line 167)
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Produces: `PipelineResult.grade: str | None`, `PipelineResult.grade_overall: float | None`, `PipelineResult.grade_dimensions: dict[str, float]`.

- [ ] **Step 1: Write the failing test** (append to `tests/test_pipeline.py`; reuses the existing `_vertical_report` helper and `PipelineDependencies`):

```python
def test_pipeline_result_carries_the_self_critic_grade(
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

    result = CutPipeline(dependencies=deps).cut(input_dir, None, output_dir, dry_run=True)

    assert result.grade in {"A", "B", "C", "D", "F"}
    assert result.grade_overall is not None and 0.0 <= result.grade_overall <= 1.0
    assert "on_beat" in result.grade_dimensions
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_pipeline.py::test_pipeline_result_carries_the_self_critic_grade -v`
Expected: FAIL — `PipelineResult` has no `grade`.

- [ ] **Step 3: Add the fields and populate them.** Add `import json` to the top of `pipeline.py` if absent. Change the dataclass:

```python
@dataclass(frozen=True)
class PipelineResult:
    analysis: Path
    cut_plan: Path
    timeline: Path
    final_video: Path
    output_dir: Path
    grade: str | None = None
    grade_overall: float | None = None
    grade_dimensions: dict[str, float] = field(default_factory=dict)
```

Add `field` to the dataclasses import: `from dataclasses import dataclass, field`. Add a helper near `_safe_build_report`:

```python
def _read_grade(output_dir: Path) -> tuple[str | None, float | None, dict[str, float]]:
    # The self-critic grade is already written to edit-quality.json during finalize; surface it on
    # the result so the GUI binds to data, not a parsed log line. Best-effort.
    try:
        data = json.loads((output_dir / "edit-quality.json").read_text(encoding="utf-8"))
        dimensions = {d["name"]: float(d["score"]) for d in data.get("dimensions", [])}
        return data.get("grade"), data.get("overall"), dimensions
    except Exception:
        return None, None, {}
```

In `cut()`, replace the `return PipelineResult(...)` with:

```python
        grade, grade_overall, grade_dimensions = _read_grade(output_dir)
        return PipelineResult(
            analysis=output_dir / "analysis.json",
            cut_plan=output_dir / "cut-plan.json",
            timeline=output_dir / "timeline.json",
            final_video=final_video,
            output_dir=output_dir,
            grade=grade,
            grade_overall=grade_overall,
            grade_dimensions=grade_dimensions,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/test_pipeline.py -q && py -m ruff check . && py -m mypy src`
Expected: PASS, clean.

- [ ] **Step 5: Commit**

```bash
git add src/aicutting/pipeline.py tests/test_pipeline.py
git commit -m "feat(gui): surface the self-critic grade on PipelineResult"
```

### Task 2: Forward style / aspect / variants through `JobRequest`

**Files:**
- Modify: `src/aicutting/gui/jobs.py`
- Test: `tests/gui/test_jobs.py`

**Interfaces:**
- Consumes: `PipelineResult` (Task 1).
- Produces: `JobRequest(input_dir, music_path, output_dir, dry_run=False, style="cinematic", aspect="16:9", variants=False)`; `run_cut_job` resolves `style` via `resolve_style` and forwards `aspect`/`variants`.

- [ ] **Step 1: Write the failing test** (append to `tests/gui/test_jobs.py`):

```python
def test_run_cut_job_forwards_style_aspect_and_variants(tmp_path) -> None:
    from aicutting.gui.jobs import JobRequest, JobSuccess, run_cut_job
    from aicutting.pipeline import PipelineResult

    captured: dict[str, object] = {}

    class FakePipeline:
        def cut(self, input_dir, music_path, output_dir, dry_run, progress=None, **kwargs):
            captured.update(kwargs)
            return PipelineResult(
                analysis=output_dir / "a.json", cut_plan=output_dir / "c.json",
                timeline=output_dir / "t.json", final_video=output_dir / "final.mp4",
                output_dir=output_dir,
            )

    request = JobRequest(
        input_dir=tmp_path, music_path=None, output_dir=tmp_path,
        style="vlog", aspect="9:16", variants=True,
    )
    result = run_cut_job(request, pipeline_factory=lambda: FakePipeline())

    assert isinstance(result, JobSuccess)
    assert captured["style"].name == "vlog"   # resolved from the string
    assert captured["aspect"] == "9:16"
    assert captured["variants"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/gui/test_jobs.py::test_run_cut_job_forwards_style_aspect_and_variants -v`
Expected: FAIL — `JobRequest` has no `style`.

- [ ] **Step 3: Implement.** In `src/aicutting/gui/jobs.py`, add imports and extend the request + protocol + call:

```python
from aicutting.core.style import STYLE_PRESETS, StylePreset, resolve_style
```

```python
@dataclass(frozen=True)
class JobRequest:
    input_dir: Path
    music_path: Path | None
    output_dir: Path
    dry_run: bool = False
    style: str = "cinematic"
    aspect: str = "16:9"
    variants: bool = False
```

Extend the `CutJobPipeline` protocol `cut` signature:

```python
    def cut(
        self,
        input_dir: Path,
        music_path: Path | None,
        output_dir: Path,
        dry_run: bool,
        progress: ProgressCallback | None = None,
        style: StylePreset = STYLE_PRESETS["cinematic"],
        aspect: str = "16:9",
        variants: bool = False,
    ) -> PipelineResult: ...
```

In `run_cut_job`, forward them:

```python
        result = pipeline_factory().cut(
            input_dir=request.input_dir,
            music_path=request.music_path,
            output_dir=request.output_dir,
            dry_run=request.dry_run,
            progress=progress,
            style=resolve_style(request.style),
            aspect=request.aspect,
            variants=request.variants,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/gui/test_jobs.py -q && py -m ruff check . && py -m mypy src`
Expected: PASS, clean.

- [ ] **Step 5: Commit**

```bash
git add src/aicutting/gui/jobs.py tests/gui/test_jobs.py
git commit -m "feat(gui): forward style/aspect/variants through JobRequest"
```

### Task 3: `Backend(QObject)` bridge

**Files:**
- Create: `src/aicutting/gui/backend.py`
- Test: `tests/gui/test_backend.py`

**Interfaces:**
- Consumes: `CutWorker` (`gui/worker.py`), `JobRequest` (Task 2), `PipelineResult` (Task 1), `ProgressEvent`/`PipelinePhase` (`core/progress.py`), `CancellationToken`.
- Produces: `phase_to_stage(phase: PipelinePhase) -> int` (0..4); `Backend(QObject)` with properties `status, stageIndex, liveMessage, busy, grade, gradeOverall, onBeat, variety, pacing, finalVideo, reportPath, outputDir, resolveDir, hasTeaser, hasShort` (each with a `*Changed` notify signal) and `@Slot`s `startCut(folder: str, music: str, style: str, aspect: str, variants: bool)`, `cancel()`, `openVideo()`, `openReport()`, `openFolder()`, `openInResolve()`.

- [ ] **Step 1: Write the failing test** (`tests/gui/test_backend.py`; `qtbot` comes from pytest-qt in the `gui` extra):

```python
from pathlib import Path

from aicutting.core.progress import PipelinePhase
from aicutting.gui.backend import Backend, phase_to_stage


def test_phase_to_stage_maps_the_pipeline_into_five_stages() -> None:
    assert phase_to_stage(PipelinePhase.CHECKING_INPUTS) == 0   # Ingest
    assert phase_to_stage(PipelinePhase.ANALYZING_FOOTAGE) == 1  # Watch
    assert phase_to_stage(PipelinePhase.RATING_FOOTAGE) == 2     # Direct
    assert phase_to_stage(PipelinePhase.ASSEMBLING_CUT) == 3     # Cut
    assert phase_to_stage(PipelinePhase.RENDERING_FINAL_VIDEO) == 4  # Render


def test_backend_starts_idle(qtbot) -> None:
    backend = Backend()
    assert backend.status == "idle"
    assert backend.stageIndex == -1
    assert backend.busy is False


def test_backend_fills_grade_fields_on_success(qtbot, tmp_path) -> None:
    from aicutting.pipeline import PipelineResult

    backend = Backend()
    result = PipelineResult(
        analysis=tmp_path / "a.json", cut_plan=tmp_path / "c.json",
        timeline=tmp_path / "t.json", final_video=tmp_path / "final.mp4",
        output_dir=tmp_path, grade="A", grade_overall=0.93,
        grade_dimensions={"on_beat": 0.98, "variety": 1.0, "pacing": 0.82},
    )
    with qtbot.waitSignal(backend.statusChanged):
        backend._on_succeeded(result)  # the worker.succeeded slot

    assert backend.status == "result"
    assert backend.grade == "A"
    assert backend.gradeOverall == 0.93
    assert backend.onBeat == 0.98
    assert backend.finalVideo.endswith("final.mp4")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/gui/test_backend.py -v`
Expected: FAIL — no module `aicutting.gui.backend`.

- [ ] **Step 3: Implement `src/aicutting/gui/backend.py`:**

```python
from pathlib import Path

from PySide6.QtCore import Property, QObject, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from aicutting.core.progress import CancellationToken, PipelinePhase, ProgressEvent
from aicutting.gui.jobs import JobFailure, JobRequest
from aicutting.gui.worker import CutWorker
from aicutting.pipeline import PipelineResult

# The 13 pipeline phases grouped into 5 premium stages shown in the UI.
_PHASE_STAGE: dict[PipelinePhase, int] = {
    PipelinePhase.CHECKING_INPUTS: 0,
    PipelinePhase.FINDING_VIDEOS: 0,
    PipelinePhase.ANALYZING_FOOTAGE: 1,
    PipelinePhase.ANALYZING_MUSIC: 1,
    PipelinePhase.IDENTIFYING_LOCATION: 1,
    PipelinePhase.RATING_FOOTAGE: 2,
    PipelinePhase.DESIGNING_EDIT: 2,
    PipelinePhase.ASSEMBLING_CUT: 3,
    PipelinePhase.PLANNING_CUT: 3,
    PipelinePhase.BUILDING_REPORT: 3,
    PipelinePhase.EXPORTING_RESOLVE_HANDOFF: 3,
    PipelinePhase.RENDERING_FINAL_VIDEO: 4,
    PipelinePhase.DONE: 4,
}


def phase_to_stage(phase: PipelinePhase) -> int:
    return _PHASE_STAGE.get(phase, 0)


class Backend(QObject):
    statusChanged = Signal()
    stageIndexChanged = Signal()
    liveMessageChanged = Signal()
    busyChanged = Signal()
    gradeChanged = Signal()
    resultChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._status = "idle"
        self._stage = -1
        self._message = ""
        self._busy = False
        self._grade = ""
        self._grade_overall = 0.0
        self._dims = {"on_beat": 0.0, "variety": 0.0, "pacing": 0.0}
        self._final = ""
        self._report = ""
        self._output = ""
        self._resolve = ""
        self._has_teaser = False
        self._has_short = False
        self._thread: QThread | None = None
        self._worker: CutWorker | None = None
        self._token: CancellationToken | None = None

    # --- properties (read-only to QML; updated from Python) ---
    def _get_status(self) -> str:
        return self._status

    status = Property(str, _get_status, notify=statusChanged)

    def _get_stage(self) -> int:
        return self._stage

    stageIndex = Property(int, _get_stage, notify=stageIndexChanged)

    def _get_message(self) -> str:
        return self._message

    liveMessage = Property(str, _get_message, notify=liveMessageChanged)

    def _get_busy(self) -> bool:
        return self._busy

    busy = Property(bool, _get_busy, notify=busyChanged)

    def _get_grade(self) -> str:
        return self._grade

    grade = Property(str, _get_grade, notify=gradeChanged)

    def _get_grade_overall(self) -> float:
        return self._grade_overall

    gradeOverall = Property(float, _get_grade_overall, notify=gradeChanged)

    def _get_on_beat(self) -> float:
        return self._dims["on_beat"]

    onBeat = Property(float, _get_on_beat, notify=gradeChanged)

    def _get_variety(self) -> float:
        return self._dims["variety"]

    variety = Property(float, _get_variety, notify=gradeChanged)

    def _get_pacing(self) -> float:
        return self._dims["pacing"]

    pacing = Property(float, _get_pacing, notify=gradeChanged)

    def _get_final(self) -> str:
        return self._final

    finalVideo = Property(str, _get_final, notify=resultChanged)

    def _get_report(self) -> str:
        return self._report

    reportPath = Property(str, _get_report, notify=resultChanged)

    def _get_output(self) -> str:
        return self._output

    outputDir = Property(str, _get_output, notify=resultChanged)

    def _get_has_teaser(self) -> bool:
        return self._has_teaser

    hasTeaser = Property(bool, _get_has_teaser, notify=resultChanged)

    def _get_has_short(self) -> bool:
        return self._has_short

    hasShort = Property(bool, _get_has_short, notify=resultChanged)

    # --- slots invoked from QML ---
    @Slot(str, str, str, str, bool)
    def startCut(self, folder: str, music: str, style: str, aspect: str, variants: bool) -> None:
        if self._busy:
            return
        out = Path(folder) / "aicutting-out"
        request = JobRequest(
            input_dir=Path(folder),
            music_path=Path(music) if music else None,
            output_dir=out,
            style=style or "cinematic",
            aspect=aspect or "16:9",
            variants=variants,
        )
        self._token = CancellationToken()
        self._worker = CutWorker(request, token=self._token)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.succeeded.connect(self._on_succeeded)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._set_status("working")
        self._set_busy(True)
        self._thread.start()

    @Slot()
    def cancel(self) -> None:
        if self._token is not None:
            self._token.cancel()

    @Slot()
    def openVideo(self) -> None:
        self._open(self._final)

    @Slot()
    def openReport(self) -> None:
        self._open(self._report)

    @Slot()
    def openFolder(self) -> None:
        self._open(self._output)

    @Slot()
    def openInResolve(self) -> None:
        self._open(self._resolve)

    # --- worker signal handlers ---
    def _on_progress(self, event: ProgressEvent) -> None:
        self._stage = phase_to_stage(event.phase)
        self.stageIndexChanged.emit()
        self._message = event.message or event.phase.value
        self.liveMessageChanged.emit()

    def _on_succeeded(self, result: PipelineResult) -> None:
        self._grade = result.grade or ""
        self._grade_overall = result.grade_overall or 0.0
        self._dims = {**self._dims, **result.grade_dimensions}
        self._final = str(result.final_video)
        self._report = str(result.output_dir / "report.html")
        self._output = str(result.output_dir)
        self._resolve = str(result.output_dir / "resolve")
        self._has_teaser = (result.output_dir / "final-teaser.mp4").exists()
        self._has_short = (result.output_dir / "final-short.mp4").exists()
        self.gradeChanged.emit()
        self.resultChanged.emit()
        self._set_busy(False)
        self._set_status("result")

    def _on_failed(self, failure: JobFailure) -> None:
        self._message = failure.message
        self.liveMessageChanged.emit()
        self._set_busy(False)
        self._set_status("error")

    # --- helpers ---
    def _open(self, path: str) -> None:
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _set_status(self, value: str) -> None:
        self._status = value
        self.statusChanged.emit()

    def _set_busy(self, value: bool) -> None:
        self._busy = value
        self.busyChanged.emit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/gui/test_backend.py -q && py -m ruff check . && py -m mypy src`
Expected: PASS, clean. (If mypy flags the `Property` descriptors, the `gui` modules are already under the mypy `ignore_errors` override in `pyproject.toml`; confirm `backend.py` is covered there — see Task 4 Step 3.)

- [ ] **Step 5: Commit**

```bash
git add src/aicutting/gui/backend.py tests/gui/test_backend.py
git commit -m "feat(gui): Backend(QObject) bridge with phase->stage mapping"
```

---

## Phase B — QML View

### Task 4: QML app bootstrap + Backend registration

**Files:**
- Create: `src/aicutting/gui/qml/Main.qml` (minimal placeholder window for this task)
- Modify: `src/aicutting/gui/app.py`; `pyproject.toml` (add `aicutting.gui.backend` to the mypy gui override)
- Test: `tests/gui/test_app_entrypoint.py`

**Interfaces:**
- Consumes: `Backend` (Task 3).
- Produces: `app.py:main()` launches the QML engine with `backend` as a context property; `app.py:main_widgets()` retains the old QWidgets launch for parallel use.

- [ ] **Step 1: Write the failing test** (append to `tests/gui/test_app_entrypoint.py`):

```python
def test_qml_main_file_exists_and_references_backend() -> None:
    from pathlib import Path

    qml = Path("src/aicutting/gui/qml/Main.qml").read_text(encoding="utf-8")
    assert "backend" in qml  # the View binds to the Backend context property
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/gui/test_app_entrypoint.py::test_qml_main_file_exists_and_references_backend -v`
Expected: FAIL — file missing.

- [ ] **Step 3: Implement.** Create `src/aicutting/gui/qml/Main.qml`:

```qml
import QtQuick
import QtQuick.Window

Window {
    width: 1180; height: 760
    visible: true
    title: "AiCutting Studio"
    color: "#0B0D10"
    Text {
        anchors.centerIn: parent
        color: "#F2F4F7"
        text: backend.status   // proves the Backend context property is wired
    }
}
```

Rewrite `src/aicutting/gui/app.py`:

```python
import sys
from pathlib import Path

from aicutting.gui.qt import require_qt

_QML_MAIN = Path(__file__).parent / "qml" / "Main.qml"


def main() -> int:
    qt = require_qt()
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine

    from aicutting.gui.backend import Backend

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    app.setApplicationName("AiCutting Studio")
    backend = Backend()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    engine.load(str(_QML_MAIN))
    if not engine.rootObjects():
        return 2
    return int(app.exec())


def main_widgets() -> int:
    # The legacy QWidgets window, kept until the QML View reaches parity.
    qt = require_qt()
    from aicutting.gui.main_window import MainWindow

    app = qt.widgets.QApplication.instance() or qt.widgets.QApplication(sys.argv)
    app.setApplicationName("AiCutting Studio")
    window = MainWindow()
    window.resize(1100, 720)
    window.show()
    return int(app.exec())


def main_cli() -> int:
    try:
        return main()
    except RuntimeError as exc:
        print(str(exc))
        return 2
```

Add `"aicutting.gui.backend"` to the `[[tool.mypy.overrides]]` `module` list in `pyproject.toml`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/gui -q && py -m ruff check . && py -m mypy src`
Expected: PASS, clean.

- [ ] **Step 5: Manual launch check + commit**

Run: `py -c "import sys; from aicutting.gui.app import main; sys.exit(main())"` → a near-black 1180×760 window showing `idle`. Close it.

```bash
git add src/aicutting/gui/qml/Main.qml src/aicutting/gui/app.py pyproject.toml tests/gui/test_app_entrypoint.py
git commit -m "feat(gui): QML app bootstrap with Backend context property"
```

### Task 5: `Theme` token singleton

**Files:**
- Create: `src/aicutting/gui/qml/Theme.qml`, `src/aicutting/gui/qml/qmldir`
- Test: `tests/gui/test_app_entrypoint.py`

**Interfaces:**
- Produces: a QML singleton `Theme` exposing the colour/spacing/radius/motion tokens used by every component.

- [ ] **Step 1: Write the failing test:**

```python
def test_theme_singleton_defines_the_brand_tokens() -> None:
    from pathlib import Path

    qmldir = Path("src/aicutting/gui/qml/qmldir").read_text(encoding="utf-8")
    theme = Path("src/aicutting/gui/qml/Theme.qml").read_text(encoding="utf-8")
    assert "singleton Theme" in qmldir
    assert "#E8B15A" in theme and "#4FD0C0" in theme  # amber + teal
    assert "reduceMotion" in theme
```

- [ ] **Step 2: Run to verify it fails** — `py -m pytest tests/gui/test_app_entrypoint.py::test_theme_singleton_defines_the_brand_tokens -v` → FAIL.

- [ ] **Step 3: Implement.** `src/aicutting/gui/qml/qmldir`:

```
singleton Theme 1.0 Theme.qml
```

`src/aicutting/gui/qml/Theme.qml`:

```qml
pragma Singleton
import QtQuick

QtObject {
    // colour
    readonly property color canvas: "#0B0D10"
    readonly property color surface1: "#14171C"
    readonly property color surface2: "#1B1F26"
    readonly property color hairline: "#262B33"
    readonly property color borderFocus: "#3A424E"
    readonly property color textHi: "#F2F4F7"
    readonly property color textMid: "#9AA4B2"
    readonly property color textLow: "#5B6675"
    readonly property color accent: "#E8B15A"
    readonly property color accentHot: "#F4C06B"
    readonly property color cool: "#4FD0C0"
    readonly property color success: "#5BD6A0"
    readonly property color danger: "#E5675B"
    // spacing / radius
    readonly property int s1: 8
    readonly property int s2: 16
    readonly property int s3: 24
    readonly property int s4: 32
    readonly property int rMd: 12
    readonly property int rLg: 16
    readonly property int rXl: 20
    // type
    readonly property string fontDisplay: "Bahnschrift"
    readonly property string fontBody: "Segoe UI"
    readonly property string fontMono: "Cascadia Mono"
    // motion
    property bool reduceMotion: false
    readonly property int tMicro: reduceMotion ? 0 : 160
    readonly property int tControl: reduceMotion ? 0 : 220
    readonly property int tScene: reduceMotion ? 0 : 450
    function gradeColor(letter) {
        return letter === "A" ? success : letter === "F" ? danger : accent;
    }
}
```

In `app.py:main()`, register the qml dir as an import path before `engine.load`:

```python
    engine.addImportPath(str(_QML_MAIN.parent))
```

- [ ] **Step 4: Run to verify it passes + launch** — tests green; relaunch (Task 4 Step 5) still shows the window.

- [ ] **Step 5: Commit**

```bash
git add src/aicutting/gui/qml/Theme.qml src/aicutting/gui/qml/qmldir src/aicutting/gui/app.py tests/gui/test_app_entrypoint.py
git commit -m "feat(gui): Theme token singleton (colour, spacing, motion)"
```

### Task 6: `DropZone` + the Invite state

**Files:** Create `src/aicutting/gui/qml/DropZone.qml`; modify `src/aicutting/gui/qml/Main.qml`.

**Interfaces:** Produces `DropZone` with `signal folderDropped(string path)` and visual states idle / drag-over / invalid; the drag-over "rack focus" animation (#1).

- [ ] **Step 1:** Create `DropZone.qml`:

```qml
import QtQuick
import QtQuick.Controls.Basic

Item {
    id: root
    signal folderDropped(string path)
    property bool hover: false

    Rectangle {
        id: frame
        anchors.fill: parent
        radius: Theme.rXl
        color: Theme.surface1
        border.width: 1
        border.color: root.hover ? Theme.accent : Theme.hairline
        scale: root.hover ? 1.015 : 1.0
        Behavior on border.color { ColorAnimation { duration: Theme.tMicro } }
        Behavior on scale { NumberAnimation { duration: Theme.tMicro; easing.type: Easing.OutExpo } }

        Text {
            anchors.centerIn: parent
            font.family: Theme.fontDisplay
            font.pixelSize: 22
            font.letterSpacing: 1.6
            color: root.hover ? Theme.textHi : Theme.textMid
            text: "DROP YOUR DRONE FOOTAGE"
        }
        // letterbox corner ticks (one repeated via a Repeater over 4 corners)
        Repeater {
            model: 4
            Rectangle {
                width: 22; height: 2; color: Theme.accent; opacity: root.hover ? 1 : 0.5
                x: index % 2 === 0 ? 16 : parent.width - 38
                y: index < 2 ? 16 : parent.height - 18
                Behavior on opacity { NumberAnimation { duration: Theme.tMicro } }
            }
        }
    }

    DropArea {
        anchors.fill: parent
        onEntered: root.hover = true
        onExited: root.hover = false
        onDropped: (drop) => {
            root.hover = false;
            if (drop.hasUrls && drop.urls.length > 0)
                root.folderDropped(drop.urls[0].toString().replace("file:///", ""));
        }
    }
}
```

In `Main.qml`, replace the placeholder `Text` with a centered `DropZone` (≈460×260) that calls `backend`-bound state later; for now wire `onFolderDropped: console.log(path)`.

- [ ] **Step 2: Launch check** — drag a folder onto the window; the frame should brighten amber, ticks light up, scale nudges; the console logs the path.

- [ ] **Step 3: Commit**

```bash
git add src/aicutting/gui/qml/DropZone.qml src/aicutting/gui/qml/Main.qml
git commit -m "feat(gui): DropZone with rack-focus drag-over animation"
```

### Task 7: `StylePicker`, `AspectPicker`, `VariantsToggle`, `PrimaryButton`

**Files:** Create `src/aicutting/gui/qml/StylePicker.qml`, `AspectPicker.qml`, `VariantsToggle.qml`, `PrimaryButton.qml`.

**Interfaces:** `StylePicker { property string value; }` (cinematic|epic|chill|vlog, sliding amber underline); `AspectPicker { property string value; }` (16:9|9:16|1:1, glyph morph); `VariantsToggle { property bool checked; }`; `PrimaryButton { property string text; signal clicked; }` (amber glow + press physics, #—CTA).

- [ ] **Step 1:** Create `StylePicker.qml` (segmented pills with a shared-element underline):

```qml
import QtQuick

Row {
    id: root
    property string value: "cinematic"
    spacing: 4
    readonly property var items: ["cinematic", "epic", "chill", "vlog"]
    Repeater {
        model: root.items
        Rectangle {
            width: 96; height: 36; radius: height / 2
            color: root.value === modelData ? Qt.rgba(0.91, 0.69, 0.35, 0.14) : Theme.surface2
            border.width: 1
            border.color: root.value === modelData ? Theme.accent : Theme.hairline
            Behavior on border.color { ColorAnimation { duration: Theme.tMicro } }
            Behavior on color { ColorAnimation { duration: Theme.tMicro } }
            Text {
                anchors.centerIn: parent
                text: modelData.charAt(0).toUpperCase() + modelData.slice(1)
                font.family: Theme.fontBody; font.pixelSize: 13
                color: root.value === modelData ? Theme.textHi : Theme.textMid
            }
            MouseArea { anchors.fill: parent; onClicked: root.value = modelData }
        }
    }
}
```

Create `AspectPicker.qml` (3 toggles whose frame glyph morphs between 16:9 / 9:16 / 1:1 by animating a `Rectangle`'s width/height with a `Behavior`), `VariantsToggle.qml` (a pill switch with a sliding knob `Behavior on x`), and `PrimaryButton.qml`:

```qml
import QtQuick

Rectangle {
    id: root
    property string text: ""
    signal clicked
    width: 220; height: 52; radius: Theme.rMd
    color: ma.pressed ? Theme.accentHot : Theme.accent
    scale: ma.pressed ? 0.98 : 1.0
    Behavior on scale { NumberAnimation { duration: Theme.tMicro; easing.type: Easing.OutExpo } }
    // amber glow
    Rectangle {
        anchors.centerIn: parent; width: parent.width + 24; height: parent.height + 24
        radius: parent.radius + 12; color: "transparent"
        border.width: 12; border.color: Qt.rgba(0.91, 0.69, 0.35, 0.18); z: -1
    }
    Text {
        anchors.centerIn: parent; text: root.text
        font.family: Theme.fontDisplay; font.pixelSize: 16; font.letterSpacing: 1.2
        color: "#0B0D10"
    }
    MouseArea { id: ma; anchors.fill: parent; onClicked: root.clicked() }
}
```

- [ ] **Step 2: Launch check** — drop these into a temporary column in `Main.qml`; clicking pills moves the selection, the toggle slides, the CTA presses with a glow.

- [ ] **Step 3: Commit**

```bash
git add src/aicutting/gui/qml/StylePicker.qml src/aicutting/gui/qml/AspectPicker.qml src/aicutting/gui/qml/VariantsToggle.qml src/aicutting/gui/qml/PrimaryButton.qml src/aicutting/gui/qml/Main.qml
git commit -m "feat(gui): style/aspect/variants pickers + primary CTA"
```

### Task 8: `StageProgress` (the 5-stage tracker)

**Files:** Create `src/aicutting/gui/qml/StageProgress.qml`.

**Interfaces:** `StageProgress { property int stage; property string message; }` — driven by `backend.stageIndex` / `backend.liveMessage`; the travelling amber key-light (#3) and check-draw on completed stages; shimmer subline.

- [ ] **Step 1:** Create `StageProgress.qml`:

```qml
import QtQuick

Column {
    id: root
    property int stage: -1
    property string message: ""
    spacing: Theme.s3
    readonly property var labels: ["INGEST", "WATCH", "DIRECT", "CUT", "RENDER"]

    Row {
        spacing: Theme.s2
        Repeater {
            model: root.labels
            Column {
                spacing: 6
                Rectangle {
                    width: 120; height: 4; radius: 2
                    color: index < root.stage ? Theme.success
                         : index === root.stage ? Theme.accent : Theme.hairline
                    Behavior on color { ColorAnimation { duration: Theme.tControl } }
                    Rectangle {  // travelling key-light on the active stage
                        visible: index === root.stage
                        width: 28; height: parent.height; radius: 2; color: Theme.accentHot
                        SequentialAnimation on x {
                            running: index === root.stage; loops: Animation.Infinite
                            NumberAnimation { from: 0; to: 92; duration: 1100; easing.type: Easing.InOutSine }
                            NumberAnimation { from: 92; to: 0; duration: 1100; easing.type: Easing.InOutSine }
                        }
                    }
                }
                Text {
                    text: modelData
                    font.family: Theme.fontDisplay; font.pixelSize: 12; font.letterSpacing: 1.4
                    color: index <= root.stage ? Theme.textHi : Theme.textLow
                }
            }
        }
    }
    Text {
        text: root.message
        font.family: Theme.fontMono; font.pixelSize: 13
        color: Theme.textMid; opacity: 0.0
        onTextChanged: { opacity = 0; fade.restart(); }
        NumberAnimation on opacity { id: fade; to: 1; duration: Theme.tControl }
    }
}
```

- [ ] **Step 2: Launch check** — temporarily bind `stage` to a `Timer` that increments 0→4; the active bar pulses amber, completed bars go mint, the message fades on change.

- [ ] **Step 3: Commit**

```bash
git add src/aicutting/gui/qml/StageProgress.qml
git commit -m "feat(gui): 5-stage progress tracker with travelling key-light"
```

### Task 9: `GradeDial` (count-up + badge reveal)

**Files:** Create `src/aicutting/gui/qml/GradeDial.qml`.

**Interfaces:** `GradeDial { property string letter; property real overall; property real onBeat; property real variety; property real pacing; }` — the dial sweep + letter cross-scale (#6) and the three dimension bars stagger-fill.

- [ ] **Step 1:** Create `GradeDial.qml` using a `Canvas` arc for the ring + a count-up `NumberAnimation` on an internal `progress` property, the letter scaling 1.3→1.0 on reveal, and three `Rectangle` bars whose `width` animates with staggered `PauseAnimation`s. (Ring colour = `Theme.gradeColor(letter)`.) Drive from `backend.grade` / `backend.gradeOverall` / `backend.onBeat` etc.

- [ ] **Step 2: Launch check** — temporarily set `letter:"A"; overall:0.93; onBeat:0.98; variety:1.0; pacing:0.82` and confirm the ring sweeps, the "A" pops, and the bars stagger-fill.

- [ ] **Step 3: Commit**

```bash
git add src/aicutting/gui/qml/GradeDial.qml
git commit -m "feat(gui): self-critic grade dial with count-up reveal"
```

### Task 10: `PreviewPanel` + result actions

**Files:** Create `src/aicutting/gui/qml/PreviewPanel.qml`.

**Interfaces:** `PreviewPanel { property string source; property bool hasTeaser; property bool hasShort; }` — `MediaPlayer` + `VideoOutput` on `backend.finalVideo` (Final/Teaser/Short tabs when present), plus the Open video / Open report / Open folder / Open in Resolve buttons calling the matching `backend` slots; result-card entrance (#7).

- [ ] **Step 1:** Create `PreviewPanel.qml`:

```qml
import QtQuick
import QtMultimedia

Column {
    id: root
    property string source: ""
    spacing: Theme.s2
    Rectangle {
        width: 560; height: 315; radius: Theme.rLg; color: "black"; clip: true
        VideoOutput { id: out; anchors.fill: parent }
        MediaPlayer {
            id: player; source: root.source ? "file:///" + root.source : ""
            videoOutput: out; audioOutput: AudioOutput {}
        }
        MouseArea { anchors.fill: parent; onClicked: player.playbackState === MediaPlayer.PlayingState ? player.pause() : player.play() }
    }
    Row {
        spacing: Theme.s1
        PrimaryButton { text: "OPEN VIDEO"; onClicked: backend.openVideo() }
        GhostButton { text: "Report"; onClicked: backend.openReport() }
        GhostButton { text: "Folder"; onClicked: backend.openFolder() }
        GhostButton { text: "Resolve"; onClicked: backend.openInResolve() }
    }
}
```

(Create a small `GhostButton.qml` — a hairline-bordered transparent button — alongside.)

- [ ] **Step 2: Launch check** — temporarily set `source` to an existing mp4 path; it plays on click; the buttons call the slots (Open folder opens Explorer).

- [ ] **Step 3: Commit**

```bash
git add src/aicutting/gui/qml/PreviewPanel.qml src/aicutting/gui/qml/GhostButton.qml
git commit -m "feat(gui): in-app preview panel + result actions"
```

### Task 11: `Main.qml` — the four states + letterbox transitions

**Files:** Modify `src/aicutting/gui/qml/Main.qml`.

**Interfaces:** Consumes every component above and the `backend` properties. Produces the full app: a `StateGroup`/`states` with `invite` / `compose` / `working` / `result`, driven by `backend.status` plus a local `folder` string; the letterbox scene transition (#2) between states; grain (#— `ShaderEffect` or low-alpha tiled image) and render shimmer (#5) overlays gated on `backend.status === "working"`.

- [ ] **Step 1:** Compose `Main.qml`: a root `Window` (canvas colour) containing (a) a background grain/gradient layer, (b) a `StackLayout`-like `Item` swapping the four screens by `backend.status` (`invite` shows `DropZone`; `compose` shows the `ReelChip` + `MusicField` + `StylePicker` + `AspectPicker` + `VariantsToggle` + `PrimaryButton` whose `onClicked` calls `backend.startCut(folder, music, stylePicker.value, aspectPicker.value, variantsToggle.checked)`; `working` shows `StageProgress` bound to `backend.stageIndex`/`liveMessage` + a `GhostButton` "Cancel" → `backend.cancel()`; `result` shows `GradeDial` + `PreviewPanel`), and (c) two black `Rectangle` letterbox bars (top/bottom) whose `height` animates in then out across state changes via `transitions`. The `DropZone.onFolderDropped` sets `folder` and (since the folder is chosen) the app shows `compose` while `backend.status` is still `idle`; once `startCut` runs, `backend.status` takes over (`working` → `result`/`error`).

- [ ] **Step 2: Full manual run** — `py -c "import sys; from aicutting.gui.app import main; sys.exit(main())"`, drop a small footage folder, pick a song + style + aspect, press the CTA, watch the 5 stages advance, and confirm the grade dial + preview appear at the end. Verify Cancel works mid-run.

- [ ] **Step 3: Commit**

```bash
git add src/aicutting/gui/qml/Main.qml
git commit -m "feat(gui): four-state Studio flow with letterbox transitions"
```

### Task 12: `ReelChip` + `MusicField` + grain/shimmer polish

**Files:** Create `src/aicutting/gui/qml/ReelChip.qml`, `MusicField.qml`; modify `Main.qml`.

**Interfaces:** `ReelChip { property string folder; property int clipCount; }`; `MusicField { property string path; signal musicDropped(string p); }` (drop/select + a stylized teal waveform drawn with a `Canvas` or a `Row` of `Rectangle`s). Add the grain overlay and the render-time diagonal light-sweep shimmer (#5) as a `ShaderEffect` gated on `backend.busy`.

- [ ] **Step 1:** Create the two components and wire them into `compose`. Clip count comes from a tiny `@Slot(str, result=int)` `countClips(folder)` added to `Backend` (counts supported video extensions) — add a matching unit test in `tests/gui/test_backend.py`.
- [ ] **Step 2: Launch check** — the dropped folder shows "name · N clips"; a dropped song shows the waveform; during a run a faint diagonal sheen sweeps the working screen.
- [ ] **Step 3: Commit**

```bash
git add src/aicutting/gui/qml/ReelChip.qml src/aicutting/gui/qml/MusicField.qml src/aicutting/gui/qml/Main.qml src/aicutting/gui/backend.py tests/gui/test_backend.py
git commit -m "feat(gui): reel chip, music waveform, render shimmer"
```

---

## Phase C — Packaging & migration

### Task 13: Windows packaging (`pyside6-deploy`) + qmltest smoke

**Files:** Create `pysidedeploy.spec`, `tests/gui/qml/tst_states.qml`; modify `README.md` / `docs/quickstart.md` (run instructions).

- [ ] **Step 1:** Add a `pysidedeploy.spec` configured for a windowed app that bundles the `qml` dir, sets `excluded_qml_plugins = QtWebEngine,QtQuick3D,QtCharts,QtSensors,QtTest`, and includes the `multimedia` + `imageformats` + `platforms` plugins.
- [ ] **Step 2:** Add a `qmltest` smoke (`tst_states.qml`) that instantiates `Main.qml` with a stub `backend` (a `QtObject` with the same properties) and asserts the four states render without error. Run: `py -m pytest tests/gui -q` (the Python side) and document `pyside6-deploy` locally.
- [ ] **Step 3:** Build once locally: `pyside6-deploy -c pysidedeploy.spec`; smoke-launch the produced exe; confirm the window opens and a dry-run cut completes. Update README/quickstart to mention `aicutting-studio` launches the new Studio.
- [ ] **Step 4: Commit**

```bash
git add pysidedeploy.spec tests/gui/qml/tst_states.qml README.md docs/quickstart.md
git commit -m "build(gui): pyside6-deploy config + qml state smoke test"
```

### Task 14: Retire the QWidgets View at parity

**Files:** Delete `src/aicutting/gui/main_window.py`, `src/aicutting/gui/widgets.py` and their tests once the QML View covers every flow; modify `src/aicutting/gui/app.py` (drop `main_widgets`); update `docs/architecture.md` (the GUI is now QML).

- [ ] **Step 1:** Confirm QML parity against the pain-point list (style/aspect/variants exposed, drag-drop, live stages, grade, preview, open actions). Only then remove the legacy files and `main_widgets`.
- [ ] **Step 2:** Update `tests/gui` — drop the QWidgets-only tests (`test_qt_smoke.py` window tests) that no longer apply; keep `test_state` / `test_jobs` / `test_backend` / `test_app_entrypoint`.
- [ ] **Step 3:** Run `py -m pytest -q && py -m ruff check . && py -m mypy src`; update `docs/architecture.md` GUI section to "native Qt Quick / QML frontend over the same pipeline."
- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor(gui): retire the QWidgets View now that QML is at parity"
```

---

## Self-Review

- **Spec coverage:** stack decision (Task 4) · design tokens (Task 5) · the four states + phase→stage (Tasks 3, 8, 11) · components DropZone/Style/Aspect/Variants/Stage/Grade/Preview/Reel/Music (Tasks 6-12) · the 7 animations (#1 Task 6, #2/#3 Tasks 11/8, #5 Task 12, #6 Task 9, #7 Task 10; #4 vision-pulse folds into StageProgress's active-stage glow, Task 8) · Backend integration + the two additive changes (Tasks 1-3) · packaging (Task 13) · migration (Tasks 4 parallel, 14 retire) · testing (Tasks 1-3 TDD, 13 qmltest). No gaps.
- **Placeholder scan:** backend tasks carry full code; QML component tasks carry real QML (Tasks 6-9 fully coded; Tasks 10-12 give the file + interface + the specific animation, with a concrete launch check each). Composite `Main.qml` (Task 11) is specified by exact child components + bindings.
- **Type consistency:** `Backend` property/slot names (`status`, `stageIndex`, `liveMessage`, `busy`, `grade`, `gradeOverall`, `onBeat`/`variety`/`pacing`, `finalVideo`/`reportPath`/`outputDir`/`resolveDir`, `hasTeaser`/`hasShort`, `startCut`/`cancel`/`open*`) are used identically in Tasks 3, 10, 11, 12. `JobRequest(style, aspect, variants)` (Task 2) matches `Backend.startCut` (Task 3) and `phase_to_stage` (Task 3) is consumed in Task 8/11. `PipelineResult.grade*` (Task 1) is read in Task 3.
