# AiCutting

[![CI](https://github.com/GeFAA/AiCutting/actions/workflows/ci.yml/badge.svg)](https://github.com/GeFAA/AiCutting/actions/workflows/ci.yml)

AiCutting is a local, Windows-first drone video cutting tool. It analyzes a
folder of footage, optionally follows a music track, rejects weak drone motion,
builds a clean cinematic timeline, and exports both a rendered video and
DaVinci Resolve handoff files.

The project is designed for creators who want an automatic first cut without
uploading their footage to a cloud service. Optional Codex or Claude Code
integration can inspect extracted screenshots and add conservative location
titles only when confidence is high.

## Current Status

AiCutting is early alpha software. The core pipeline, desktop launcher, CLI,
FFmpeg render path, Resolve handoff artifacts, motion rejection, beat-aware
planning, and optional local agent location titles are implemented and covered
by automated tests. The user experience is still being refined.

### AI Drone Director 3.0

AiCutting's current planning engine is the agent-driven AI Drone Director 3.0
path, which turns on automatically for drone footage. It:

- samples the footage into contact sheets and asks the local vision agent
  (Codex, falling back to Claude Code) to rate each moment, classify the drone
  shot, and reject takeoff, landing, search-flight, shaky, and boring frames,
- turns the music into a beat grid that fills the whole song, with clip lengths
  driven by energy (calm = longer clips, drops = fast cuts on the beat),
- lets the agent design the edit — which moment fills each slot, the arc, and
  where strong effects fit — then assembles it deterministically with variety
  guards (no repeats, no identical shots back to back, spread across files),
- renders real effects (zoom push-in, varied transitions) only where they fit,
- writes auditable review artifacts for every stage.

If no local agent is available (or the installed agent is outdated), a
deterministic fallback editor still produces a full-length, beat-synced,
effect-aware edit offline. The agent needs a current Codex or Claude Code CLI.

## Highlights

- Local video analysis for drone and landscape B-roll.
- Motion scoring that rejects shaky yaw, search-flight, takeoff, and landing
  segments when they are not useful for a clean edit.
- Optional music analysis for beat and energy-aware cuts.
- Confidence-gated location titles via local Codex or Claude Code backends.
- Native Windows desktop entry point with `Start AiCutting.cmd`.
- CLI for repeatable runs and dry-run artifact checks.
- FFmpeg renderer plus Resolve handoff exports under `resolve/`.
- AI Drone Director 3.0 planning: agent-rated footage, beat-driven full-length
  edits, and motion-aware effects (details below).
- JSON artifacts for auditability, including `analysis.json`, `cut-plan.json`,
  `timeline.json`, `director-report.json`, `rejected-segments.json`,
  `footage-ratings.json`, `rhythm-grid.json`, `edit-decision.json`, and
  `director-3-report.json`.

## Quick Start

### Option 1: Windows Desktop

1. Install Python 3.11 or newer.
2. Install FFmpeg and make sure `ffmpeg` and `ffprobe` are available on `PATH`.
3. Clone or download this repository.
4. Double-click [Start AiCutting.cmd](Start%20AiCutting.cmd).
5. Select a video folder, optional music file or folder, and an output folder.
6. Start the cut and review the generated output files.

The launcher first tries to use your existing Python environment. If required
dependencies are missing, it can create a local `.venv` automatically.

### Option 2: Command Line

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[gui]"
```

Run the desktop app:

```powershell
aicutting-studio
```

Run an automatic cut:

```powershell
aicutting cut .\input-videos --music .\music.mp3 --out .\output
```

Create artifacts without rendering the final video:

```powershell
aicutting cut .\input-videos --out .\output --dry-run
```

More detailed setup notes are in [docs/quickstart.md](docs/quickstart.md).

## Requirements

- Windows 10 or newer is the primary target.
- Python 3.11 or newer.
- FFmpeg on `PATH`.
- Optional: DaVinci Resolve for importing the handoff files.
- Optional: Codex or Claude Code on `PATH` for automatic location titles.

## Local AI Agent Behavior

AiCutting does not require an API key for the core cut pipeline. If Codex or
Claude Code is available locally, AiCutting extracts a few representative
screenshots from strong footage candidates and asks the local agent for a
structured location suggestion. The title is rendered only when the suggestion
passes the confidence gate.

If no agent is available, or if the agent is uncertain, AiCutting writes the
reason to `location-suggestions.json` and omits the title overlay.

## Privacy

The deterministic pipeline works locally on your machine. Video files are read
from the folders you select and outputs are written to your chosen output
folder. Optional Codex or Claude Code behavior depends on those tools and their
own account settings, so review their configuration before using agent-assisted
location titles on private footage.

## Development

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[dev,gui]"
py -m pytest
py -m ruff check .
py -m mypy src
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.
See [SECURITY.md](SECURITY.md) for security and private-footage notes.

## Roadmap

- Improve the non-technical desktop workflow and error recovery.
- Add stronger visual review tools for rejected and selected segments.
- Expand Resolve integration beyond interchange exports.
- Add more robust packaging for non-developer installation.
- Continue improving motion, beat, and location-title quality on real drone
  projects.

## Author

AiCutting is created and maintained by [GeFAA](https://github.com/GeFAA).

## License

AiCutting is released under the MIT License. See [LICENSE](LICENSE).
