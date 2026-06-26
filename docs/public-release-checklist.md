# Public Release Checklist

Use this before making the GitHub repository public.

## Repository

- README explains what AiCutting does and its current alpha status.
- Quickstart guide works for a fresh Windows checkout.
- LICENSE is present and referenced.
- CONTRIBUTING.md explains development and PR expectations.
- CI is enabled for pushes and pull requests.
- Issue and pull request templates are present.

## Safety

- No private footage, rendered videos, local outputs, or credentials are
  committed.
- Generated output folders are ignored.
- Optional Codex and Claude Code behavior is documented as local-agent
  dependent.
- Low-confidence location guesses are not rendered into final video.

## Verification

Run before public launch:

```powershell
py -m pytest
py -m ruff check .
py -m mypy src
```

## First Public Description

Suggested short repository description:

```text
Local AI-assisted drone video cutting pipeline with FFmpeg rendering, Resolve handoff, and optional Codex/Claude location titles.
```
