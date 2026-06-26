# Quick Start

This guide is for first-time users who want to run AiCutting from a local
checkout.

## 1. Install Python

Install Python 3.11 or newer from https://www.python.org/downloads/.

On Windows, the `py` launcher is recommended. Check it with:

```powershell
py --version
```

## 2. Install FFmpeg

AiCutting uses FFmpeg for probing and rendering video.

After installation, these commands should work in a new terminal:

```powershell
ffmpeg -version
ffprobe -version
```

## 3. Start The Desktop App

For the simplest path on Windows, double-click:

```text
Start AiCutting.cmd
```

The launcher checks whether the required Python packages are already available.
If they are missing, it can create a local `.venv` and install the GUI
dependencies.

## 4. Choose Inputs

In AiCutting Studio, select:

- A folder containing drone or landscape videos.
- An optional music file or music folder.
- An output folder.

The output folder is where AiCutting writes the rendered video and all review
artifacts.

## 5. Review Outputs

Typical output files:

- `final.mp4`: rendered edit.
- `analysis.json`: detected media facts and scored clip candidates.
- `cut-plan.json`: selected edit plan.
- `timeline.json`: neutral timeline used by render and Resolve export.
- `director-report.json`: selection decisions and warnings.
- `rejected-segments.json`: rejected footage with reasons.
- `location-suggestions.json`: optional location title suggestions.
- `resolve/`: FCPXML, EDL, and media manifest for DaVinci Resolve.

## Command Line Usage

Install in editable mode:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[gui]"
```

Run a cut:

```powershell
aicutting cut .\input-videos --music .\music.mp3 --out .\output
```

Create review artifacts without rendering:

```powershell
aicutting cut .\input-videos --out .\output --dry-run
```

Launch the GUI:

```powershell
aicutting-studio
```

## Optional Local Agent Titles

If Codex or Claude Code is installed on `PATH`, AiCutting can ask the local
agent to identify a conservative location title from extracted screenshots. If
the agent is uncertain, the final video will not render a title.

This keeps the default behavior safe: low-confidence guesses are stored as
artifacts, not burned into the video.

## Troubleshooting

### The launcher says Python is missing

Install Python 3.11 or newer and reopen the launcher.

### Rendering fails

Make sure `ffmpeg` and `ffprobe` are available on `PATH`.

### The launcher cannot install dependencies

Check free disk space on the drive that contains the repository. Python video
and GUI dependencies can be large.

### No location title appears

Check `location-suggestions.json`. AiCutting intentionally omits title overlays
when confidence is too low or no local agent backend is available.
