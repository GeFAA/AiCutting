# AiCutting Studio — desktop rework (design)

**Date:** 2026-06-28
**Status:** design, pending implementation plan

## Goal

Rework the AiCutting Studio desktop app into an ultra-modern, lightweight, beautifully
animated frontend over the existing local pipeline. Keep the cut quality and the Python
pipeline exactly as-is; replace only the View. Expose the 4.0 options the CLI already has
(`--style`, `--aspect`, `--variants`) and surface the self-critic grade as a first-class result.

## Decision: build the View in PySide6 Qt Quick / QML

The non-visual layer is already View-agnostic and well-tested — `gui/worker.py`
(`CutWorker(QObject)` on a `QThread`), `gui/jobs.py`, `gui/state.py` (the idle/ready/running/
complete/failed/cancel job state machine), `core/progress.py` (`ProgressEvent` + the
`PipelinePhase` enum), and `pipeline.py`. QML reuses all of it unchanged; only `app.py`,
`main_window.py`, and `widgets.py` are replaced.

**Why QML over the alternatives:**

- **QWidgets + QSS + QPropertyAnimation** — lowest effort, but structurally caps the headline
  feature: smooth continuous motion, shaders (grain/shimmer), and choreographed multi-element
  transitions are painful and often janky in retained-mode widgets. Rejected as the primary
  (kept as the parallel fallback during migration).
- **Qt Quick / QML** — *recommended.* GPU scene-graph at 60fps, declarative `States`/
  `Transitions`/`Behavior`, `ShaderEffect` for grain & light-sweeps. The job state machine maps
  1:1 onto a QML `StateGroup`. Same Qt signal/slot bridge we already use; same light packaging
  (no second runtime — only the QtQuick plugins are added). Satisfies *modern + animated +
  lightweight + keep Python* simultaneously.
- **Tauri/Electron + React** — highest visual ceiling but discards our cleanest asset (the Qt
  pipeline integration), ships the heaviest (Chromium / a bundled second Python runtime), and
  forces an IPC bridge to stream `ProgressEvent`s. Rejected.

## Visual identity

**"The colour-grading suite at midnight."** A near-black graphite canvas, a recurring 2.39:1
letterbox framing motif (thin cinematic bars + corner ticks as the app's signature device), a
whisper of film grain (low-alpha shader), and a single warm golden-hour amber key accent against
a cool teal — the orange-and-teal blockbuster grade, fitting for a cutting tool and distinct from
blue/purple SaaS dashboards. Generous negative space; editorial, credits-roll typography.
Premium and restrained, never neon.

### Colour tokens
```
Canvas        #0B0D10   Surface-1   #14171C   Surface-2   #1B1F26
Hairline      #262B33   Border-focus #3A424E
Text-hi       #F2F4F7   Text-mid    #9AA4B2   Text-low    #5B6675
Accent (key)  #E8B15A   amber — brand, primary CTA, active state
Accent-hot    #F4C06B   Cool (fill) #4FD0C0   teal — AI/analyze, waveform, secondary
Success       #5BD6A0   Danger      #E5675B
Grade ring    F→A: #E5675B → #E8B15A → #5BD6A0
```

### Typography (Windows-first, cross-platform fallbacks)
- **Display / stage labels** → `Bahnschrift` (variable condensed grotesk, ships with Win10/11),
  UPPERCASE +6–8% tracking. Fallback `"Oswald","Segoe UI Semibold",sans-serif`.
- **Body / controls** → `Segoe UI Variable` → `"Segoe UI"` → `system-ui`.
- **Numerals / timecode / grade count-up** → `Cascadia Mono` → `"Consolas"` (tabular figures so
  the dial and live timecode don't shimmer).

### Spacing / radius / elevation / motion
- Spacing 8px base: 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64.
- Radius: sm 8 (chips) · md 12 (inputs/buttons) · lg 16 (cards) · xl 20 (drop zone) · full (pills).
- Elevation (dark UI → light + border, not heavy shadow): step surface lightness, 1px top inner
  highlight `rgba(255,255,255,0.04)`, ambient shadow `rgba(0,0,0,0.45)` (blur 24, y 8); an amber
  glow (`#E8B15A` ~18%, blur 28) reserved only for the primary CTA and the grade badge.
- Motion tokens: micro 160ms, control 220ms, scene 450ms; `easeOutExpo` entrances,
  `easeInOutCubic` scene swaps. One shared token set + a global **Reduce Motion** switch.

## Flow — one window, four states

Smart defaults make the happy path **drop → press one button**: Style = Cinematic, Aspect = 16:9,
Variants = off, Output = auto next to the source folder.

- **State 0 · Invite.** Full-bleed canvas, large centred drop zone inside letterbox corner ticks:
  "Drop your drone footage." Slow drifting gradient + grain loop behind.
- **State 1 · Compose.** The folder collapses into a *reel chip* (name · N clips). One tidy column:
  **Music** (optional drop/select → stylized teal waveform), **Style** (4 pills), **Aspect** (3
  frame-icon toggles), **Variants** ("Also make teaser + short"), and the glowing CTA **"Direct the
  cut."** An *Advanced* disclosure hides output path, dry-run, and the live log.
- **State 2 · Working.** Compose letterboxes away; a **5-stage cinematic tracker** takes over with
  the live `ProgressEvent.message` streaming as a timecode-styled subline and an indeterminate
  shimmer bar (the backend reports phases, not %, so the UI shows honest stage progress — never a
  fabricated percentage). A quiet ghost **Cancel** wired to the existing `CancellationToken`.
- **State 3 · Result.** Bars part to reveal an in-app **preview** (`MediaPlayer` + `VideoOutput` on
  `final.mp4`; Final / Teaser / Short tabs when variants ran) beside the **grade dial** + three
  dimension bars, then actions: **Open video · Open report · Open folder · Open in Resolve**, and a
  one-line director's note from the critic detail.

### Phase → stage mapping
Group the 13 `PipelinePhase` values into 5 stable, premium stages; stream the fine phase as the
subline:
1. **Ingest** — `CHECKING_INPUTS`, `FINDING_VIDEOS`
2. **Watch** — `ANALYZING_FOOTAGE`, `ANALYZING_MUSIC`, `IDENTIFYING_LOCATION`
3. **Direct** (the marquee AI beat) — `RATING_FOOTAGE`, `DESIGNING_EDIT`
4. **Cut** — `ASSEMBLING_CUT`, `PLANNING_CUT`, `BUILDING_REPORT`, `EXPORTING_RESOLVE_HANDOFF`
5. **Render** — `RENDERING_FINAL_VIDEO` → `DONE` triggers the Result reveal.

## Components
- **DropZone** (`DropArea`, hairline rounded frame + letterbox corner ticks; idle / drag-over /
  populated / invalid), **ReelChip**, **MusicField** (+ teal waveform), **StylePicker** (4
  segmented pills, sliding amber underline), **AspectPicker** (3 frame-icon toggles whose glyph
  morphs the ratio), **VariantsToggle**, **StageProgress** (5-stage tracker driven by a QML
  `StateGroup`), **GradeDial** (red→amber→mint ring + centre letter + 3 dimension bars),
  **PreviewPanel / ResultCard**, **PrimaryButton** (glow + press physics), **GhostButton**,
  **Advanced disclosure**. Build on QtQuick.Controls **Basic** and skin custom controls (avoid
  Material/Fusion so the look stays bespoke).

## Signature animations (restrained, premium, tied to the app)
1. **Drag-over rack focus** — frame brightens to amber, corner ticks expand, blurred backdrop
   *sharpens* (a focus pull), scale 1.0→1.015; on drop, a fast **shutter wipe** confirms ingest.
2. **Letterbox scene transitions** — Compose→Working→Result masked by 2.39:1 bars sliding in then
   parting (~450ms), reinforcing the identity and hiding layout reflow.
3. **Stage handoff** — the amber key-light glow travels along the filmstrip to the next stage; the
   finished stage draws a check (stroke-dash) and dims to mint; the live message cross-fades like a
   ticking timecode.
4. **Vision-agent "alive" pulse** — during `RATING_FOOTAGE` the Direct stage breathes a slow glow
   and a scan-line shimmer sweeps a row of tiny clip thumbnails — the AI visibly looking at shots.
5. **Render shimmer** — during `RENDERING_FINAL_VIDEO` a slow diagonal light-sweep shader glides
   across a grainy placeholder — the "developing" feel.
6. **Grade count-up + badge reveal** — the dial sweeps 0%→`overall` with a decelerating land; the
   letter cross-scales in (1.3→1.0) with an amber/mint bloom; the three dimension bars stagger-fill
   80ms apart. One confident landing — no confetti.
7. **Result card entrance** — preview rises 16px and fades in with light parallax as the bars part;
   action buttons stagger in; Open video / Open report get a one-time amber sheen.

Global discipline: prefer opacity/transform over layout/blur; cache grain/shimmer via
`layer.enabled`; honour Reduce Motion; 60fps budget on integrated graphics.

## Architecture — Python ↔ QML

**Reused unchanged:** `pipeline.py`, `core/progress.py`, `gui/jobs.py`, `gui/worker.py`,
`gui/state.py`.

**New `app.py`:** bootstrap `QGuiApplication` + `QQmlApplicationEngine`, load `main.qml`.

**New `Backend(QObject)`** exposed to QML (`setContextProperty("backend", …)`), owning the
`QThread` + `CutWorker` exactly as `main_window.py` does today:
- `Q_PROPERTY` (each with a notify signal QML binds to and animates via `Behavior`): `status`,
  `stageIndex`, `liveMessage`, `busy`, `grade`, `gradeOverall`, `onBeat`/`variety`/`pacing`,
  `finalVideo` / `reportPath` / `outputDir` / `resolveDir`, `hasTeaser` / `hasShort`.
- `Slot`s invokable from QML: `startCut(folder, music, style, aspect, variants)`, `cancel()`,
  `openVideo()`, `openReport()`, `openFolder()`, `openInResolve()`.
- `worker.progress` → a slot that maps `ProgressEvent.phase` → `stageIndex` and sets
  `liveMessage` (queued connection marshals to the GUI thread — existing thread-safety holds).
  `worker.succeeded` → fills grade + result properties → `status` = Result; `worker.failed` →
  error state.

**Two small, additive backend changes (no pipeline-behaviour change):**
1. Forward `style` / `aspect` / `variants` through `JobRequest` + `run_cut_job` (the pipeline
   already accepts them; the GUI currently forwards only `dry_run`).
2. Surface the critic result as **structured fields on `PipelineResult`** (`grade: str`,
   `grade_overall: float`, the three dimension scores) instead of parsing the log line, so the
   dial binds cleanly. The pipeline already computes `EditQuality` at finalize — purely additive.

## Windows packaging
- `pyside6-deploy` (Nuitka) → single windowed app; no new runtime vs the QWidgets app, only the
  QtQuick QML plugins (~150–250 MB folder).
- Trim with `excluded_qml_plugins` (drop QtWebEngine / QtQuick3D / QtCharts / QtSensors / QtTest if
  unused). Always include the `platforms` and `imageformats` plugin folders (blank-window gotcha).
- Preview player: QtMultimedia's FFmpeg backend is default on Windows in Qt 6.8+ — collect the
  multimedia + ffmpeg plugins for `MediaPlayer`. This is separate from the pipeline's own
  `ffmpeg.exe` used for rendering; keep both.
- Rely on the Qt Quick Compiler (qmlcachegen) for fast startup; build windowed (no console); keep
  the `aicutting-studio` console script for dev. Code-signing is a follow-up (SmartScreen).

## Migration strategy
Add QML as a *parallel* `Backend`-driven entrypoint; the working QWidgets app keeps running until
QML reaches parity. Port the existing `test_state` / `test_worker` / `test_jobs` unchanged; add Qt
Quick Test (`qmltest`) smoke tests for the state machine. Retire QWidgets only at parity.

## Testing
- Keep/extend the Python-side tests (`tests/gui/test_state.py`, `test_jobs.py`, `test_app_entrypoint.py`).
- New: `Backend` unit tests (the phase→stage mapping, the additive JobRequest forwarding, result
  field surfacing) drivable without a display. `qmltest` smoke tests for the four states.
- The two additive changes (JobRequest forwarding, PipelineResult grade fields) get TDD coverage.

## Risks & mitigations
1. **Rebuild regression / lost time** — keep the whole non-View layer intact and tested; run QML
   in parallel; retire QWidgets only at parity.
2. **QML deploy fragility on Windows** — stand up `pyside6-deploy` early; pin `excluded_qml_plugins`;
   smoke-launch the packaged app on a clean Windows run; keep a PyInstaller fallback documented.
3. **"Flashy not premium" drift / progress honesty** — one motion-token system + Reduce Motion;
   cap concurrent animations; opacity/transform over blur; 60fps budget; stage-based progress that
   never fabricates a percentage and never shows a preview before `final.mp4` exists.

## Out of scope (YAGNI for this rework)
Job history, batch queue, in-app report rendering (we open `report.html`), telemetry, settings UI
beyond Advanced disclosure, and saved input profiles. These are post-rework candidates.
