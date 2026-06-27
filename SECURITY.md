# Security Policy

AiCutting is beta software. Review the local agent behaviour below before using
it with sensitive footage.

## Reporting A Vulnerability

Open a GitHub issue if the report does not contain private information. If the
issue involves private footage paths, credentials, or account details, avoid
posting them publicly and describe the problem at a high level first.

## Local Data Notes

- The core pipeline processes files from the folders you select.
- Output artifacts are written to your selected output folder.
- **What the vision agent sees:** when a Codex or Claude Code backend is on
  `PATH`, AiCutting sends extracted **frames of your footage** to that local
  agent — a few location screenshots, and (in the AI Drone Director 3.0 path)
  contact-sheet thumbnails sampled across your clips for shot rating. These are
  handled by that tool and its account configuration; review them before running
  on private footage. Run with no agent on `PATH` to keep the pipeline fully
  deterministic and offline.
- Do not commit private footage, rendered outputs, or generated artifacts to the
  repository.
