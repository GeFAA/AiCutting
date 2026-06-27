# AI Drone Director 4.0 — Wave 1

The first, highest-leverage slices of the [4.0 roadmap](../../ROADMAP.md). Each ships behind the
existing deterministic fallbacks, stays beat-exact, and is TDD'd + visually verified before commit.

## Pillar A — Cinematic colour grade (render) — *visible win*
The look jumps from "clean" to "graded". Apply a tasteful, subtle cinematic grade to every clip in
the render (gentle contrast + saturation, restrained teal-orange split-tone) so the whole film
shares one professional colour. `color_intent` finally means something.
- `render/ffmpeg.py`: insert a `_color_grade()` filter into the per-clip chain (after `format`,
  before the Ken Burns animation so the grade rides through the zoom).
- Test: the per-clip filter contains the grade. Verify: render a graded vs ungraded frame, confirm
  it reads cinematic, not over-cooked.

## Pillar B — Motion-aware selection (analysis + pipeline) — *shot quality*
The vision agent re-derives motion from a still; meanwhile `analysis/motion.py` +
`analysis/drone_shots.py` already score smoothness, jitter, search-flight and takeoff/landing per
candidate — and the 3.0 path ignores them. Wire them in: bias moment sampling toward the smooth,
cinematic regions of each file and deterministically drop the shaky / descent moments, so fewer bad
shots reach the agent at all.

## Pillar C — Phrase-aware beat grid (planning) — *timing*
`build_beat_plan` already detects `downbeats_s` + `phrase_boundaries_s`; `build_rhythm_grid` walks
raw beats and ignores them. Snap slot boundaries and accents to downbeats, and let phrase
boundaries start fresh pacing sections, so the cut breathes with the song's structure.

## Order & method
A (instant visible win) → B (shot quality) → C (timing). Each pillar: write the failing test,
implement, run `pytest`/`ruff`/`mypy`, render + inspect real frames, commit as GeFAA. Later waves
take on grading-match, stabilisation, speed ramps, social reframe, presets, and the self-critic.
