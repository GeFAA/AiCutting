# Architecture

AiCutting turns a folder of drone clips into a finished cinematic cut around a neutral
timeline core. The live planner is **AI Drone Director 3.0**: a vision agent rates the
footage, a deterministic director sequences it by colour onto a beat-exact grid, and the
renderer adds motion, transitions, and a cinematic title.

## Pipeline (`CutPipeline.cut`)

1. **Analyse footage & music.** Discover clips and the optional track, probe them, score
   motion, and turn the music into a full-length beat grid with an energy curve.
2. **Identify the location.** Extract a few representative frames and ask the local vision
   agent (Codex, falling back to Claude Code) to name the region; the title is
   confidence-gated.
3. **Sample & rate moments.** Sample the footage across all files into labelled contact
   sheets and ask the vision agent to rate each moment — keeping sharp, well-composed shots
   with real depth and rejecting takeoff, landing, low/ground passes, shaky, and flat-texture
   frames.
4. **Diversify.** Drop near-duplicate keeps (same file + shot type within a few seconds).
5. **Sequence by colour.** Compute a per-moment colour signature and order the kept shots
   into a coherent journey (dark lava grouped first, flowing into green).
6. **Assemble on the beat.** Lay the colour-ordered shots onto the energy-driven beat grid so
   every cut lands exactly on the beat; flow gentle crossfades through the calm sections and
   keep the drops as punchy hard cuts.
7. **Compose the title.** Overlay the place (where) over the recording date (when, parsed from
   the footage metadata).
8. **Write artifacts & report.** Emit the JSON artifacts and a self-contained `report.html`.
9. **Export the Resolve handoff** (FCPXML + EDL + media manifest).
10. **Render `final.mp4`** with FFmpeg — per-clip Ken Burns push-ins, the crossfade chain, and
    the luma-occluded cinematic title reveal.

If no vision agent is available (or it is too old), a deterministic fallback editor still
produces a full-length, beat-synced edit from safe-zone candidates.

## Module boundaries (`src/aicutting/`)

- `core`: shared models, errors, path validation, artifact IO, progress events.
- `analysis`: deterministic facts — discovery, ffprobe, motion / drone-shot scoring, audio &
  beat analysis, footage metadata, colour signatures, and contact-sheet sampling.
- `director`: the vision agents (location recognition, moment rating) and review models.
- `planning`: target duration, the rhythm / beat grid, colour sequencing, and beat-exact
  timeline assembly.
- `render`: FFmpeg command construction, Ken Burns motion, and the cinematic title overlay.
- `report`: the self-contained `report.html` generator.
- `resolve`: FCPXML, EDL, and media-manifest export.
- `agents`: local Codex / Claude Code detection.
- `tui`: the live terminal progress view.
- `gui`: the PySide6 desktop frontend over the same pipeline.
- `pipeline` / `cli`: orchestration and the command-line entry point.

## Desktop GUI

AiCutting Studio is a native PySide6 frontend over the same pipeline. GUI modules collect
local paths, validate readiness, run `CutPipeline` in a background worker, stream progress,
and open the outputs. They do not own edit decisions.

Progress is reported with shared `ProgressEvent` values from `aicutting.core.progress`; the
CLI renders them as a rich live view, the GUI as user-facing phases.

## Transparency & graceful degradation

Every stage writes an auditable JSON artifact, and `report.html` shows a thumbnail and the
reason for every kept clip. The vision agent improves selection, location, and the title, but
the deterministic path remains the fallback source of truth — so a run never breaks when the
agent or a model is unavailable, and footage never leaves the machine.
