# Architecture

AiCutting turns a folder of drone clips into a finished cinematic cut around a neutral timeline
core. A vision agent rates the footage, a deterministic director sequences it by colour onto a
beat-exact grid, the renderer adds motion, a cinematic grade and a title, and a self-critic grades
the result — all local, all transparent.

## Pipeline (`CutPipeline.cut`)

1. **Analyse footage & music.** Discover clips and the optional track, probe them, score motion,
   and turn the music into a full-length beat grid with an energy curve.
2. **Identify the location.** Extract a few representative frames and ask the local vision agent
   (Codex, falling back to Claude Code) to name the region; the title is confidence-gated.
3. **Sample, gate & rate moments.** Sample the footage across all files; **motion-gate** out shaky
   and searching moments *before* the agent ever sees them; build labelled contact sheets and ask
   the vision agent to rate each moment — keeping sharp, well-composed shots with real depth and
   rejecting takeoff, landing, low/ground passes, shaky, and flat-texture frames; then **diversify**
   to drop near-duplicate keeps.
4. **Sequence by colour.** Compute a per-moment colour signature and order the kept shots into a
   coherent journey (dark lava grouped first, flowing into green).
5. **Assemble on the beat.** Lay the colour-ordered shots onto the energy-driven, phrase-aware grid
   so every cut lands exactly on a beat (snapped to downbeats, never crossing a phrase boundary);
   slow-mo the calm establishing shots (still beat-exact), flow gentle crossfades through the calm
   sections, and keep the drops as punchy hard cuts. Dynamic shots gravitate to the drops and
   establishing shots to the calm sections (the **musical-structure arc**), within the colour
   journey. The chosen **style preset** tunes pace, slow-mo, transitions and grade across the run.
6. **Finish the timeline.** Crown the **hero shot** on the biggest beat (a pronounced push-in),
   **level** tilted horizons, **colour-match** the clips toward one consistent look, apply the
   cinematic **colour grade**, **reframe** to the requested aspect (16:9 master, or a cover-cropped
   9:16 / 1:1 social master whose crop slides toward each subject), then run the read-only
   **self-critic**, which grades the cut (on-beat, variety, pacing) into `edit-quality.json`. A weak
   agent cut is **re-planned** against the deterministic fallback and the better-grading one is kept
   — but a strong cut is never silently altered.
7. **Compose the title.** Overlay the place (where) over the recording date (when, parsed from the
   footage metadata).
8. **Write artifacts & report.** Emit the JSON artifacts and a self-contained `report.html` (which
   surfaces the self-critic grade).
9. **Export the Resolve handoff** (FCPXML + EDL + media manifest).
10. **Render `final.mp4`** with FFmpeg — per-clip Ken Burns push-ins, slow-mo, the colour grade, the
    aspect cover-crop, the crossfade chain, and the luma-occluded cinematic title reveal. With
    `--variants`, also render a 15 s teaser and a 60 s short master beside it.

If no vision agent is available (or it is too old), a deterministic fallback editor still produces
a full-length, beat-synced edit from safe-zone candidates.

## Module boundaries (`src/aicutting/`)

- `core`: shared models, errors, path validation, artifact IO, progress events, and the **style
  presets** (`core/style.py`).
- `analysis`: deterministic facts — discovery, ffprobe, motion / drone-shot scoring, audio & beat
  analysis, footage metadata, colour signatures, contact-sheet sampling, **cross-clip colour
  matching** (`color_match.py`), **horizon detection** (`horizon.py`), and the **content-aware
  reframe** offsets (`content_reframe.py`).
- `director`: the vision agents (location recognition, moment rating), the beat-plan model, and
  review models.
- `planning`: target duration, the phrase-aware rhythm / beat grid, colour sequencing (with the
  musical-structure arc), beat-exact timeline assembly, the **hero moment** (`planning/hero.py`),
  and the **length variants** (`planning/variants.py`).
- `render`: FFmpeg command construction (Ken Burns motion, slow-mo, colour grade & match, horizon
  rotation, the title overlay) and the **aspect reframe** (`render/reframe.py`).
- `quality`: the **self-critic** that grades the finished cut and its **re-plan** loop
  (`quality/critic.py`).
- `report`: the self-contained `report.html` generator (including the self-critic panel).
- `resolve`: FCPXML, EDL, and media-manifest export.
- `agents`: local Codex / Claude Code detection.
- `tui`: the live terminal progress view.
- `gui`: the PySide6 desktop frontend over the same pipeline.
- `pipeline` / `cli`: orchestration and the command-line entry point.

## Desktop GUI

AiCutting Studio is a native PySide6 frontend over the same pipeline. GUI modules collect local
paths, validate readiness, run `CutPipeline` in a background worker, stream progress, and open the
outputs. They do not own edit decisions.

Progress is reported with shared `ProgressEvent` values from `aicutting.core.progress`; the CLI
renders them as a rich live view, the GUI as user-facing phases.

## Transparency & graceful degradation

Every stage writes an auditable JSON artifact (including `edit-quality.json`, the self-critic
grade), and `report.html` shows a thumbnail and the reason for every kept clip alongside the grade.
The vision agent improves selection, location, and the title, but the deterministic path remains the
fallback source of truth — so a run never breaks when the agent or a model is unavailable, and
footage never leaves the machine.
