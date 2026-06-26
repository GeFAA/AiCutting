# Contributing

Thanks for taking a look at AiCutting. The project aims to become a serious
local tool for automatic drone video editing, so changes should be small,
tested, and easy to review.

## Development Setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[dev,gui]"
```

## Required Checks

Run these before opening a pull request:

```powershell
py -m pytest
py -m ruff check .
py -m mypy src
```

## Pull Request Guidelines

- Keep changes focused on one topic.
- Include tests for behavior changes.
- Update documentation when user-facing behavior changes.
- Do not commit private footage, generated renders, or large media files.
- Mention external tool requirements such as FFmpeg, Resolve, Codex, or Claude
  Code when they matter for review.

## Project Boundaries

The deterministic pipeline should remain usable without Codex, Claude Code, or
any paid API. Agent-assisted features are optional helpers and must fail safely.

JSON artifacts are part of the product. When changing analysis, planning,
rendering, or Resolve export behavior, preserve clear artifacts that explain
what happened.

## Reporting Bugs

Use the bug report template and include:

- Command or GUI workflow used.
- Python version.
- FFmpeg version.
- Whether Codex or Claude Code was installed.
- Relevant output artifact paths.

Do not upload private raw footage unless you are sure it is safe to share.
