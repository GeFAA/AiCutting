# AI Drone Director 3.0 — Design

## Why

The 2.0 director path produces unprofessional output on real footage. Evidence from
`Downloads\est-aicutting-output` (real run):

- **Length:** the timeline has exactly **4 clips × 5 s = 20 s** while `target_duration_s = 180`.
  `_build_drone_director_20_plan` emits only the 4 story-arc clips and ignores the music/target
  length entirely. This is the core defect.
- **Bad footage selected:** a near-takeoff window (`src 7–12 s` of a source file) was used. The
  motion classifier is a crude bright-centroid proxy and lets gentle takeoff/landing descents
  through as `pull_back`/`top_down`.
- **Feels random:** 4 clips are picked from 64 "good" candidates by a shaky per-role heuristic;
  every transition is a `hard_cut` and nothing is beat-synced.

Note: the codex/claude screenshot location pipeline IS integrated and working (the run produced
`location-agent-response.codex.json`, `location-screenshots/`, and a real suggestion). That part
is out of scope here.

## Goal

Replace the 4-clip story arc with a **professional, full-length, beat-driven, curated edit**:
fill the whole music track, cut on the beat with energy-driven pacing, robustly reject bad
footage (takeoff/landing/jitter/search), curate for quality and variety (not random), and apply
**strong, real effects only where they fit**. Deterministic and local; the codex location titles
stay as-is.

## Requirements (from brainstorming)

1. **Length = music length.** The cut fills the whole song, beat-synced, ending when the music ends.
2. **Pacing = dynamic by energy.** Calm passages → longer clips (a few beats); drops/peaks → fast
   cuts (½–1 beat). Cuts always land on beats.
3. **Effects = as impressive as possible, but only when they fit.** Clean beat cuts are the
   backbone; at drops/peaks with matching shot motion, apply real effects (zoom push-in, speed
   accent, whip/slide transition, match-cut). Confidence-gated and frequency-limited.
4. **No bad footage.** Strict rejection of takeoff, landing, search-flight, unstable yaw, jitter,
   and low technical quality.
5. **Not random.** No duplicate/overlapping source windows, no same shot type back-to-back, spread
   across all source files, intensity matched to music energy.

## Approach

**Chosen: A — evolve the planner ("AI Drone Director 3.0").** Keep the working 2.0 building blocks
(shot classification, beat plan, audit artifacts) and replace the weak story-arc selection and the
placeholder effect rendering with a real beat-driven editor. Rejected: B (full rewrite — too large,
discards working code) and C (minimal loop patch — keeps random selection and placeholder effects).

## Architecture

New deterministic stages, wired into `build_cut_plan` for drone material (style
`ai_drone_director_30`):

```
AudioAnalysis ─┐
               ▼
         beat_plan (existing)
               ▼
      rhythm grid  (NEW planning/rhythm.py)   → ordered beat-snapped slots over full song
               ▼
   curated selection (NEW planning/selection.py) → best non-repeating candidate per slot
               ▼
     effect plan (planning/effects.py, reworked) → gated real effects per cut
               ▼
        timeline   (planning/engine.py)        → TimelineClips with effects
               ▼
     ffmpeg render (render/ffmpeg.py, reworked) → real zoompan / xfade-variety / speed
```

Each unit has one purpose and a clear interface, testable in isolation.

### 1. Candidate generation & rejection (`analysis/video.py`, `analysis/drone_shots.py`)

- **Takeoff/landing trim:** do not generate candidate windows within the first/last
  `TAKEOFF_LANDING_TRIM_S` (default 12 s) of each source file — that is where takeoff and landing
  occur. Guard: if a file is shorter than `2 × trim + min_window`, fall back to a proportional trim
  so short clips still yield candidates.
- **Denser candidates:** reduce the window stride (e.g. 2.5 s) so there are many unique windows to
  fill a full-song grid without repetition.
- **Stricter rejection:** keep motion rejection (jitter / search / unstable / edge takeoff-landing)
  and the `searching` override; add a technical-quality floor (sharpness+contrast) below which a
  candidate is rejected. Rejected candidates are still recorded in `shot-candidates.json`.

### 2. Rhythm grid (`planning/rhythm.py`, NEW)

`build_rhythm_grid(beat_plan, target_duration_s) -> list[RhythmSlot]`.

- Walks the beats across the **whole** music duration (capped at `target_duration_s`).
- Each slot spans an integer number of beats chosen from local energy: high energy → 1 beat
  (or ½ on strong drops), low energy → 3–4 beats. Slot boundaries are exact beat timestamps.
- Each `RhythmSlot` carries: `start_s`, `end_s` (timeline), `duration_s`, `energy`, `section`
  label, and `is_accent` (peak/drop → eligible for effects).
- No music → a default visual grid (~2.5 s slots) covering a footage-derived target duration.

### 3. Curated selection (`planning/selection.py`, NEW)

`select_clips(slots, candidates) -> list[SelectedClip]`.

- Accepted candidates only (rejection already applied).
- Greedy per slot, scored by: shot-type ↔ slot-energy fit (calm → establishing/top_down/orbit;
  high → reveal/approach/fly_through), `drone_director_score`, and variety penalties.
- **Hard constraints:** never reuse the same source window; never the same `shot_type` as the
  immediately previous slot; cap consecutive clips from one source file (spread).
- **Reuse policy:** if unique candidates run out before the grid is full, allow a window to repeat
  only with a minimum spacing (e.g. ≥ 20 s apart) and prefer a different sub-segment; if even that
  is exhausted, end the edit early rather than pad with garbage (and warn).
- Each `SelectedClip` records the chosen source sub-segment (slot duration taken from the candidate)
  and the reason.

### 4. Effect planning (`planning/effects.py`, reworked)

`build_effect_plan(selected, slots) -> EffectPlan`.

- Backbone: `HARD_CUT` on every beat boundary.
- At `is_accent` slots **and** when shot motion supports it, choose one real effect:
  - forward motion (approach/reveal/fly_through) on a peak → **smooth push-in (zoompan)** +
    `SMOOTH_ZOOM` transition,
  - strong lateral (tracking/orbit) on a drop → **whip/slide** transition,
  - two adjacent shots with aligned motion → **match-cut** (hard cut, motion-matched),
  - calm intro/outro → **dissolve**.
- Frequency cap: no two effect cuts back-to-back; a max effect ratio (e.g. ≤ 30 % of cuts) so
  effects stay special. Each decision is confidence-gated and carries its parameters.

### 5. Real effect rendering (`render/ffmpeg.py`, reworked)

Replace the placeholder "everything renders as `fade`" with real filters, each verified against
real ffmpeg (like the earlier drawtext fix):

- **Transitions:** use the actual `xfade` transition catalogue (`fade`, `fadeblack`, `smoothleft`,
  `slideup`, `circleopen`, …) mapped per effect kind, not just `fade`.
- **Push-in / zoom:** `zoompan` on the incoming clip for a gradual punch-in over its duration.
- **Speed accent:** `setpts` to speed up (or briefly slow) an accented clip for emphasis.
- Filtergraph is assembled and validated; a real render smoke test confirms each effect parses and
  produces video. Risky filters fall back to a clean hard cut rather than failing the render.

### 6. Integration (`planning/engine.py`, `pipeline.py`)

- `build_cut_plan` routes drone material (any `shot_type != UNKNOWN`) to `build_director_3_plan`,
  which runs grid → selection → effects → timeline. Style `ai_drone_director_30`; notes updated.
- The legacy (non-drone) path is unchanged.
- Pipeline keeps all audit artifacts (`shot-candidates.json`, `beat-plan.json`, an updated
  `edit/story-plan`, `effect-plan.json`, `director-…-report.json`) and the codex location titles.

## Data flow

`AnalysisReport` (with drone shot fields) → `beat_plan` → `rhythm grid` → `selection` →
`effect plan` → `Timeline` (`TimelineClip`s carrying transition + effect params) → ffmpeg render +
Resolve export. JSON artifacts written at each stage for auditability.

## Error handling / edge cases

- **No music:** default visual rhythm grid; effects limited to the calm set.
- **Too little footage:** spacing-limited reuse; if still short, produce a shorter edit + a report
  warning rather than padding with rejected footage.
- **Single source file:** trim still applied; variety enforced across windows of that file.
- **Effect render failure:** per-effect fallback to a clean hard cut; the overall render never fails
  because of an effect.

## Testing

- **rhythm:** grid fills (≈) the full music duration; slots snap to beats; durations track energy.
- **trim/rejection:** candidates inside takeoff/landing zones are excluded; quality floor rejects
  low-detail frames.
- **selection:** no duplicate windows; no same shot type back-to-back; spread across files; fills the
  grid; reuse only with spacing.
- **effects:** effects only at accents and when motion fits; frequency cap respected.
- **ffmpeg:** each effect kind renders under real ffmpeg (smoke test); fallbacks work.
- **real footage:** full run on `Downloads\est` → length ≈ music, zero takeoff/landing in the
  timeline, varied non-repeating cuts, effects only at peaks; render a preview and watch it.

## Out of scope

- ML/optical-flow shot understanding (the bright-centroid proxy is improved by trimming + stricter
  rules, not replaced).
- True keyframed speed ramps (a constant speed accent is used instead).
- Changes to the codex/claude location-title pipeline.
