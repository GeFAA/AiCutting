# AiCutting Desktop Frontend Design

Date: 2026-06-20

## Goal

AiCutting needs a real desktop frontend for users who do not know command lines,
FFmpeg, Python environments, or editing pipeline details. The first GUI should make
the normal workflow feel like:

1. choose a folder with drone videos,
2. optionally choose a music file,
3. choose or accept an output folder,
4. press start,
5. open the finished result.

The frontend must feel professional and long-term maintainable. It is not a toy
mockup and it must not duplicate the editing logic already implemented in the
pipeline.

## Approved Decisions

- Frontend type: native Python desktop app.
- GUI toolkit: PySide6 / Qt for Python.
- Layout: guided one-window app.
- Default workflow: `Cinematic Auto` preset with sensible defaults.
- Target user: non-technical local users who want an automatic drone edit.
- Existing CLI: remains supported and must not regress.
- Pipeline ownership: the existing `CutPipeline` remains the source of truth.
- Advanced features: logs, dry run, agent backend status, and Resolve artifacts are
  available behind a details/advanced area, not in the main path.
- Web app and Tauri/Electron shell are out of scope for this first frontend.

## User Experience

The app is called **AiCutting Studio**. It opens directly into the working screen,
not a landing page.

The main screen contains:

- video folder picker,
- optional music picker,
- output folder picker with an automatic default,
- preset selector with `Cinematic Auto` selected by default,
- clear start/cancel controls,
- status and progress area,
- compact details/log panel,
- result actions after completion.

The main path should avoid technical wording. The user should not need to understand
analysis artifacts, timelines, codec probing, or Resolve exports to get a finished
video. Technical details are still available for debugging and professional review.

After a successful run, the app shows:

- finished video path,
- button/action to open `final.mp4`,
- button/action to open the output folder,
- links or labels for `analysis.json`, `cut-plan.json`, `timeline.json`,
- Resolve handoff folder status.

## Architecture

The GUI lives inside the existing Python package under `aicutting.gui`.

Planned modules:

- `aicutting.gui.app`: app entry point, Qt application setup, theme setup.
- `aicutting.gui.main_window`: guided main window composition.
- `aicutting.gui.state`: immutable or simple typed UI state for paths, preset, and job status.
- `aicutting.gui.worker`: background worker that runs the pipeline without freezing the UI.
- `aicutting.gui.widgets`: small reusable widgets for path selection, status, logs, and results.

The current pipeline remains the shared engine. The GUI may add optional progress
callbacks or status hooks to the pipeline, but the CLI and GUI must call the same
core behavior.

The first implementation should expose a console script such as `aicutting-studio`
or `aicutting gui`. Packaging into a Windows installer is a follow-up release step,
but the code should be structured so PyInstaller or a similar packager can be added
without rewriting the app.

## Data Flow

1. User selects the video folder.
2. The GUI validates that the folder exists and contains supported videos.
3. User optionally selects a music file or folder.
4. The GUI proposes a default output folder, usually next to the source or under a
   user-selected destination.
5. User clicks start.
6. A background worker calls `CutPipeline.cut(...)`.
7. The pipeline reports coarse progress phases back to the GUI.
8. The worker emits success or failure.
9. The GUI displays result actions or a friendly error.

The GUI should never construct timeline decisions itself. Its role is to collect
inputs, launch the pipeline, present progress, and expose results.

## Job States

The desktop app should use explicit states:

- `idle`: nothing selected yet.
- `ready`: valid source and output paths are available.
- `running`: the worker is active and controls are locked where needed.
- `complete`: result artifacts are available.
- `failed`: a user-friendly error and technical details are available.
- `cancel_requested`: the user asked the worker to stop when safe.

The start button is enabled only when the app is `ready`. During `running`, the app
keeps rendering progress visible and prevents path changes that would invalidate the
active job.

## Progress Model

The GUI should show coarse, stable phases instead of pretending to know exact render
percentages when the backend cannot guarantee them.

Initial phases:

- `Checking inputs`
- `Finding videos`
- `Analyzing footage`
- `Analyzing music`
- `Planning cut`
- `Exporting Resolve handoff`
- `Rendering final video`
- `Done`

If the pipeline cannot provide fine-grained progress yet, the GUI should still show
which phase is active and stream useful log lines.

## Error Handling

Errors must be understandable for non-technical users and useful for debugging.

The GUI should handle and explain:

- missing video folder,
- no supported video files,
- unreadable music file,
- missing output permissions,
- missing FFmpeg or ffprobe,
- pipeline failure,
- render failure,
- Resolve handoff failure.

User-facing messages should say what happened and what to try next. Technical details
belong in the details/log area so issues can still be reported on GitHub.

## Testing Strategy

The first GUI implementation should avoid fragile full visual automation unless it
is needed. The stable parts should be tested directly:

- GUI state transitions,
- path validation helpers,
- worker behavior with a mocked pipeline,
- pipeline progress callback behavior,
- CLI behavior after GUI additions,
- package script/import behavior.

Manual smoke testing should cover:

- launching the desktop app,
- selecting folders/files,
- start button enable/disable behavior,
- a dry or mocked run,
- a real small run when FFmpeg is available,
- completion and failure screens.

## Out of Scope

- full NLE timeline editing,
- manual clip trimming in the GUI,
- cloud rendering,
- multi-user accounts,
- web dashboard,
- Tauri/Electron shell,
- fully packaged installer in the first GUI implementation,
- replacing DaVinci Resolve or FFmpeg with an embedded editor.

## Definition of Done

The first desktop frontend is done when a developer can install the project, launch
AiCutting Studio, select a video folder and optional music, start the job, observe
clear progress, and reach either a friendly failure or a finished output folder.

The CLI must still pass its existing tests, and GUI-specific logic must have focused
tests so the frontend can grow without becoming fragile.
