# AiCutting

AiCutting is a professional local CLI/agent pipeline for automatically cutting drone and landscape B-roll into clean cinematic edits.

It is Windows-first for the MVP, uses deterministic analysis and timeline planning, and produces both a direct FFmpeg render and a DaVinci Resolve handoff.

## What It Does

- Finds supported drone video files in an input folder.
- Optionally analyzes a music track for beat and energy information.
- Builds an adaptive clean cinematic timeline.
- Writes `analysis.json`, `cut-plan.json`, and `timeline.json`.
- Extracts review screenshots from strong footage candidates and asks a local
  Codex/Claude backend for a conservative location title.
- Renders location text only when the agent returns high confidence.
- Renders `final.mp4` with FFmpeg.
- Exports Resolve handoff files under `resolve/`.
- Writes director artifacts such as `director-report.json`,
  `rejected-segments.json`, and `location-suggestions.json`.

## Install For Development

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[dev]"
```

If your `python` command points to the Microsoft Store alias on Windows, use the `py` launcher as shown above.

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

## Basic Usage

```powershell
aicutting cut ./input --music ./music --out ./out
```

For a no-render artifact check:

```powershell
aicutting cut ./input --out ./out --dry-run
```

## External Tools

Install FFmpeg and ensure `ffmpeg` and `ffprobe` are available on `PATH`.

For automatic location titles, install either Codex or Claude Code on `PATH`.
Codex is preferred when both are available because it can receive extracted
screenshots directly. If no agent backend is available, AiCutting still runs and
omits the title overlay safely.

DaVinci Resolve handoff starts with FCPXML, EDL, and a media manifest. Full Resolve scripting is intentionally separated from the first deterministic handoff path.

## Development Checks

```powershell
py -m pytest
py -m ruff check .
py -m mypy src
```
