# AiCutting

AiCutting is a professional local CLI/agent pipeline for automatically cutting drone and landscape B-roll into clean cinematic edits.

It is Windows-first for the MVP, uses deterministic analysis and timeline planning, and produces both a direct FFmpeg render and a DaVinci Resolve handoff.

## What It Does

- Finds supported drone video files in an input folder.
- Optionally analyzes a music track for beat and energy information.
- Builds an adaptive clean cinematic timeline.
- Writes `analysis.json`, `cut-plan.json`, and `timeline.json`.
- Renders `final.mp4` with FFmpeg.
- Exports Resolve handoff files under `resolve/`.
- Detects local Codex and Claude Code backends for optional agent workflows.

## Install For Development

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[dev]"
```

If your `python` command points to the Microsoft Store alias on Windows, use the `py` launcher as shown above.

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

DaVinci Resolve handoff starts with FCPXML, EDL, and a media manifest. Full Resolve scripting is intentionally separated from the first deterministic handoff path.

## Development Checks

```powershell
py -m pytest
py -m ruff check .
py -m mypy src
```

