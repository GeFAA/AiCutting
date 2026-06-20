# AiCutting MVP Design

Date: 2026-06-20

## Goal

AiCutting is a professional local AI-assisted video cutting tool for drone and landscape B-roll. The MVP should take a folder of drone videos, optional music, and an output folder, then automatically produce:

- a finished cinematic `.mp4`,
- structured analysis and edit artifacts,
- a DaVinci Resolve handoff from the first version.

The product is not a toy editor or a template generator. It should make clean, cinematic, sensible edits from drone footage with tasteful transitions, rhythm-aware cuts when music is present, and a workflow that is reproducible enough for a serious GitHub project.

## Approved Decisions

- Product shape: hybrid CLI/agent tool.
- First interface: professional CLI/agent workflow, not a GUI.
- Editing target: drone and landscape B-roll, not social-media shorts.
- Editor integration: DaVinci Resolve support starts in the MVP.
- Platform strategy: Windows-first, with portable abstractions for later macOS/Linux support.
- Agent strategy: local Codex and Claude Code backends, optimized for subscription-based local usage rather than API-token dependency.
- Automation level: fully automatic.
- Duration: automatic based on material amount and quality, defaulting to cinematic and not hectic.
- Music: optional, but central when present. With music, cuts align to beats and energy.
- Analysis: hybrid. Classical video/audio analysis is required; vision/LLM analysis is optional.
- Style: adaptive clean cinematic.
- Color: adaptive technical correction plus a subtle cinematic look when appropriate.

## Architecture

AiCutting uses a central timeline core. The timeline core owns all edit decisions once, then sends those decisions to output adapters.

Inputs flow through deterministic analysis modules that produce structured metadata. The edit decision engine turns that metadata into a neutral timeline model containing clip selections, trim ranges, order, pacing, beat alignment, transition choices, speed-ramp intent, and color intent.

Two output adapters consume the same timeline:

- FFmpeg renders a finished video directly.
- DaVinci Resolve export creates a professional handoff for editor-native finishing.

Codex and Claude Code are local agent backends above the pipeline. They can inspect artifacts, review cut plans, explain decisions, and later improve configuration or heuristics. They do not replace the deterministic pipeline, because core behavior must remain testable and reproducible.

## Modules

### `aicutting analyze`

Reads videos and optional music. Produces metadata and signals:

- ffprobe stream metadata,
- scene boundaries,
- blur and sharpness scores,
- exposure and contrast signals,
- motion and stability scores,
- visual diversity hints,
- beat grid and energy curve when music is provided.

Output: `analysis.json`.

### `aicutting plan`

Builds the automatic cut plan from analysis output. It decides:

- target duration,
- segment ranking,
- story order,
- shot length,
- beat alignment,
- transition type,
- speed-ramp intent,
- color intent.

Output: `cut-plan.json` and `timeline.json`.

### `aicutting render`

Renders the neutral timeline through FFmpeg. It should prioritize repeatable output and readable logs over hidden editor state.

Output: finished `.mp4` and render logs.

### `aicutting resolve`

Creates the DaVinci Resolve handoff from the same timeline. The MVP target is a Resolve-importable timeline export, starting with FCPXML plus a media manifest and an EDL fallback for simple timelines. The adapter should also detect common Windows Resolve install locations and report whether deeper Resolve scripting is available, but full remote control of Resolve is not required for the MVP.

Output: Resolve handoff artifacts.

### `aicutting agent`

Detects available local agent tools such as Codex and Claude Code. It can run optional review or improvement tasks against pipeline artifacts.

Agent behavior must be additive. If no agent is available, the core cut pipeline still works.

## Data Flow

1. User runs `aicutting cut ./input --music ./music --out ./out`.
2. The CLI validates paths, tools, codecs, and output location.
3. Analysis extracts video and audio signals into `analysis.json`.
4. Planning creates `cut-plan.json` and `timeline.json`.
5. FFmpeg renders the final video.
6. Resolve export writes editor handoff artifacts.
7. Optional agent review writes notes or updated recommendations without hiding the deterministic artifacts.

The output directory is the audit trail. A failed run should still leave useful logs and partial artifacts when possible.

## Editing Logic

The default style is adaptive clean cinematic.

AiCutting prioritizes segments that are stable, sharp, well exposed, visually distinct, and compositionally useful. It avoids shaky footage, boring long straight flights, harsh exposure jumps, repeated near-identical shots, and unusable codec/media failures.

Without music, it builds a natural cinematic sequence with restrained pacing. With music, it uses beat and energy analysis:

- calm sections receive longer shots,
- stronger music moments receive tighter cuts,
- energy peaks can trigger stronger visual moments,
- speed ramps and motion matches are used only when both footage and music justify them.

Transitions remain professional:

- hard cuts are the default,
- short dissolves are used sparingly,
- match cuts use compatible motion or composition,
- dynamic transitions are reserved for clearly supported moments.

Color is adaptive:

- first normalize technical issues such as exposure, contrast, and saturation,
- then apply only a subtle cinematic intent,
- avoid aggressive looks that damage drone footage.

## Error Handling

The CLI should fail clearly and usefully. It must report:

- missing FFmpeg or ffprobe,
- missing or unsupported DaVinci Resolve integration path,
- unreadable video files,
- unsupported or broken codecs,
- missing input folders,
- invalid music files,
- too little usable footage,
- output permission failures.

Errors should appear in terminal output and logs. Where practical, structured status should also be written for agent review.

## Testing Strategy

The MVP should start with focused tests around the stable core:

- timeline and cut-plan models,
- target duration selection,
- clip ranking,
- beat alignment,
- transition selection,
- output adapter boundaries,
- CLI validation behavior.

Video-heavy tests should use small fixtures or mocked analysis results so CI remains fast. Real sample footage can be added later as an optional integration test suite.

## GitHub Quality Bar

The first public-ready project structure should include:

- clear README with installation and usage,
- architecture documentation,
- example configuration,
- issue templates,
- pull request template,
- license,
- CI for tests and linting,
- professional package metadata,
- a concise roadmap that does not overpromise.

## Out of Scope for MVP

- social-media shorts and captions,
- full GUI or desktop app,
- cloud rendering,
- multi-user SaaS,
- aggressive auto-grading,
- guaranteed full remote control of every Resolve installation,
- paid API dependency as a core requirement.

## MVP Definition of Done

A user on Windows can run:

```powershell
aicutting cut ./input --music ./music --out ./out
```

and receive a finished cinematic video, structured analysis artifacts, a cut plan, a neutral timeline, logs, and a DaVinci Resolve handoff.
