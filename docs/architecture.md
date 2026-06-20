# Architecture

AiCutting is built around a neutral timeline core.

## Pipeline

1. Validate input paths and output folder.
2. Discover video and optional music files.
3. Analyze media into `analysis.json`.
4. Build an adaptive clean cinematic `cut-plan.json`.
5. Write the neutral `timeline.json`.
6. Render `final.mp4` with FFmpeg.
7. Export DaVinci Resolve handoff artifacts.

## Module Boundaries

- `core`: shared models, errors, path validation, artifact IO.
- `analysis`: deterministic video/audio facts.
- `planning`: target duration, ranking, transitions, timeline construction.
- `render`: FFmpeg command construction and execution.
- `resolve`: FCPXML, EDL, and media manifest export.
- `agents`: local Codex and Claude Code detection.
- `pipeline`: orchestration.

## Desktop GUI

AiCutting Studio is a native PySide6 desktop frontend over the same pipeline. GUI
modules live under `aicutting.gui` and do not own edit decisions. They collect
local paths, validate readiness, run `CutPipeline` in a background worker, show
progress events, and expose the output artifacts.

Pipeline progress is represented with shared `ProgressEvent` values from
`aicutting.core.progress`. The CLI can ignore these callbacks, while the GUI uses
them for stable user-facing phases.

## Long-Term Rule

Agent features may improve review and configuration, but deterministic artifacts remain the source of truth. This keeps the project testable and usable without paid API calls.
