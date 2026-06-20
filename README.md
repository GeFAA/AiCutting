# AiCutting

AiCutting is a professional local CLI/agent pipeline for automatically cutting drone and landscape B-roll into clean cinematic edits.

The MVP targets Windows first and produces both a direct FFmpeg render and a DaVinci Resolve handoff from the same neutral timeline.

## MVP Command

```powershell
aicutting cut ./input --music ./music --out ./out
```

## Development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m mypy src
```
