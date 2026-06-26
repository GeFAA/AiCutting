# Security Policy

AiCutting is early alpha software. Please do not use it with sensitive footage
unless you understand the local toolchain and optional agent behavior.

## Reporting A Vulnerability

Open a GitHub issue if the report does not contain private information. If the
issue involves private footage paths, credentials, or account details, avoid
posting them publicly and describe the problem at a high level first.

## Local Data Notes

- The core pipeline processes files from the folders you select.
- Output artifacts are written to your selected output folder.
- Optional Codex or Claude Code location-title features depend on those local
  tools and their account configuration.
- Do not commit private footage, rendered outputs, or generated artifacts to the
  repository.
