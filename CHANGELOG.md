# Changelog

All notable changes to AiCutting are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project uses
[Semantic Versioning](https://semver.org/).

## [4.1.2] — 2026-06-28

### Fixed
- **The cut was capped at 75 s for songs between 45 s and 240 s**, so a 3-minute track produced a
  75 s edit that used only a fraction of the good footage and cut the song short. The target now
  matches the song length (clamped 15–300 s), so the whole track plays and the cut showcases the
  footage. Verified on a real cut: 14 → 30 distinct good scenes used.

## [4.1.1] — 2026-06-28

### Fixed
- **Cuts landed off the beat when the song's first beat is early.** A small lead-in (e.g. a first
  beat at 0.26 s) was too short for an intro slot, so the rhythm grid started at the first beat
  instead of at 0; the assembled timeline was then offset from the music and every cut landed
  ~0.26 s early (the self-critic correctly graded such a cut F). The grid now always starts at
  t=0. Verified on a real song: 0/13 → 13/13 cuts on the beat, 0 ms drift.

## [4.1.0] — 2026-06-28

### Added — a real desktop app
- **AiCutting Studio**, rebuilt in PySide6 **Qt Quick / QML** over the unchanged pipeline. Identity:
  "the colour-grading suite at midnight" — near-black graphite, amber + teal, a 2.39:1 letterbox
  motif, seven restrained signature animations.
- **Choose footage by drag-drop _or_ a native folder dialog**; pick a song by drop or a file
  dialog; an **Advanced** disclosure for the output folder and a dry-run toggle.
- A **live working view**: as the cut runs it shows what the AI is doing right now — the location
  frame it found, the contact-sheet thumbnails it is rating (with a determinate `done/total` bar and
  a kept/rejected count), then the chosen-clip thumbnails — driven by a pure
  `live_view(phase, output_dir)` resolver reading the pipeline's artifacts.
- A **result screen** with the self-critic grade dial (the ring counts up and colours by grade) and
  an in-app preview poster with Open video / report / folder / Resolve.
- The GUI now exposes the 4.0 options it was missing: `--style`, `--aspect`, `--variants`, dry-run,
  and the self-critic grade.
- `pyside6-deploy` packaging config (`pysidedeploy.spec`) for a standalone Windows app.

### Added — cut quality
- **Cross-clip colour matching** — every clip nudged toward one consistent look.
- **Horizon levelling** — clips with a clearly tilted horizon rotated back to level.
- **Hero moment on the drop** — the clip on the biggest beat gets a pronounced push-in.
- **Musical-structure arc** — dynamic shots gravitate to the drops, establishing shots to the calm
  sections, within the colour journey.
- **Self-critic re-plan** — a weak cut is re-planned against the deterministic fallback; the
  better-grading one is kept.
- **Content-aware reframe** — the vertical/square crop slides toward each shot's subject.

### Changed
- Retired the legacy QWidgets window; the QML Studio is the only frontend. The folder validator is
  wired into the new Backend, so an empty footage folder is rejected before a run starts.

### Fixed
- CI now installs the `gui` extra and runs the Qt/QML tests headless (offscreen), so the suite is
  green with the desktop app included.

## [4.0.0] — 2026-06-27

### Added
- The **AI Drone Director** cinematic cut: motion-aware selection, a phrase-aware beat grid
  (cuts on downbeats), a cinematic colour grade, slow-mo speed ramps, style presets
  (`--style cinematic|epic|chill|vlog`), vertical / square social masters (`--aspect 9:16|1:1`),
  length variants (`--variants` → teaser + short), and the read-only self-critic that grades the
  finished cut and surfaces it in `report.html`.

[4.1.2]: https://github.com/GeFAA/AiCutting/releases/tag/v4.1.2
[4.1.1]: https://github.com/GeFAA/AiCutting/releases/tag/v4.1.1
[4.1.0]: https://github.com/GeFAA/AiCutting/releases/tag/v4.1.0
[4.0.0]: https://github.com/GeFAA/AiCutting/releases/tag/v4.0.0
