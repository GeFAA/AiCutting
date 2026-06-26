# AI Drone Director 3.0 — Design (agent-driven)

## Why

The 2.0 director path produces unprofessional output on real footage. Evidence from
`Downloads\est-aicutting-output` (real run):

- **Length:** the timeline has exactly **4 clips × 5 s = 20 s** while `target_duration_s = 180`.
  `_build_drone_director_20_plan` emits only the 4 story-arc clips and ignores the music length.
- **Bad footage selected:** a near-takeoff window (`src 7–12 s`) was used; the crude bright-centroid
  motion classifier cannot tell a gentle landing/takeoff from a `pull_back`/`top_down`.
- **Feels random:** 4 clips picked from 64 "good" candidates by a shaky heuristic; every transition
  is `hard_cut`, nothing beat-synced.

The codex/claude screenshot pipeline is already integrated and working (the run produced
`location-agent-response.codex.json`, `location-screenshots/`, a real suggestion). 3.0 leans into
that capability.

## Goal

A **professional, full-length, beat-driven edit whose creative judgment is made by the local
vision agent (codex, fallback claude)** — the agent that can actually *see* the frames — rather
than by brittle deterministic heuristics. Deterministic code is kept to the minimum where it is
genuinely better than an LLM (beat timing from audio, timeline assembly, FFmpeg rendering) and as
an offline fallback.

## Requirements

1. **Length = music length**, beat-synced; fills the whole song. Fixes the 20 s.
2. **Pacing = dynamic by energy** (calm → longer clips, drops → fast cuts), cuts on beats.
3. **Effects = as strong as possible, only where they fit** — real zoom/whip/speed at peaks when
   the shot motion supports it; clean beat cuts otherwise.
4. **No bad footage** — takeoff, landing, search, shaky, boring are rejected.
5. **Not random** — varied, well-ordered, intensity matched to the music.
6. **Decisions are agent-driven (codex/claude), not deterministic.** The agent rates footage,
   rejects bad moments, selects and orders the edit, and suggests effect moments. Deterministic
   code only does beat timing, assembly, rendering, and the no-agent fallback.

## Approach

**Chosen: A — evolve the planner into an agent-driven editor ("AI Drone Director 3.0").** Reuse the
existing agent plumbing (`agents/backends.py`, `analysis/screenshots.py`, the codex/claude
`exec --image … --output-schema` pattern from `director/location.py`) and extend it from "location
titles" to "edit decisions". Keep beat detection, assembly, and rendering deterministic. Rejected:
a purely deterministic editor (the crude classifier is exactly what failed) and a from-scratch ML
pipeline (too large).

## Architecture

```
videos ─► keyframes + contact sheets (det.)
music  ─► beat/energy grid (det.)
                 │
        ┌────────┴─────────┐
        ▼                  ▼
  AGENT: rate footage   AGENT: design the edit
  (codex sees frames,   (given kept moments +
   per-moment quality,   music structure → ordered
   shot type, keep/      clip list, arc, effect
   reject + reason)      moments)
        └────────┬─────────┘
                 ▼
   deterministic assembly onto the beat grid ─► Timeline ─► real FFmpeg render
                 ▲
        deterministic fallback editor (used only if no agent / agent fails)
```

### 1. Keyframe + contact-sheet extraction (deterministic — `analysis/screenshots.py` extended)

Sample frames across each source file (respecting a takeoff/landing trim of the first/last ~12 s),
labelled with their source file + timestamp, and tile them into **contact sheets** (grids of
~12–16 thumbnails) so one vision call covers many moments. Sampling density is bounded so the total
number of agent calls stays small (target ≤ ~15 calls for a full project).

### 2. Agent footage rating (`director/edit_agent.py` NEW — codex/claude)

For each contact sheet, the agent receives the image + a strict JSON schema and acts as a
professional drone editor: per labelled moment it returns `cinematic_score` (0–1), `shot_type`,
`keep` (bool) and a `reason` (e.g. "landing", "takeoff", "boring sky", "shaky", "strong reveal").
This **replaces** the bright-centroid classifier as the source of quality/rejection truth. Calls
are batched, results cached to disk per project, and parsed with the existing
`parse_*_agent_response` robustness (fenced JSON, result-wrapper, etc.).

### 3. Beat/energy grid (deterministic — `planning/rhythm.py` NEW)

Music → a sequence of beat-snapped slots covering the whole song; slot length follows local energy
(high → ½–1 beat, low → 3–4 beats). Each slot carries `start/end`, `energy`, `section`, `is_accent`.
This stays deterministic — beat detection is math the LLM cannot do from frames. No music → a
default visual grid over a footage-derived duration.

### 4. Agent edit decision (`director/edit_agent.py` — codex/claude)

A second agent call receives the **kept, rated moments** (file, timestamp, score, shot type) plus a
compact description of the **music structure** (duration, number of slots, per-section energy) and
returns the **ordered edit**: which moment fills each slot/section, the overall arc, and which cuts
should get a strong effect (and which kind). This is the creative editing decision, made by the
agent. Output is a strict JSON schema, validated and parsed.

### 5. Deterministic assembly (`planning/engine.py`)

Map the agent's ordered moments onto the beat grid: each chosen moment becomes a `TimelineClip` of
its slot's duration, with the transition/effect the agent (or the gating rules) assigned. Enforce
safety invariants the agent might violate: no duplicate/overlapping source window, no two identical
shots back-to-back, spread across files, slot durations from the grid. `build_cut_plan` routes drone
material here; style `ai_drone_director_30`.

### 6. Real effect rendering (`render/ffmpeg.py`, reworked)

Replace the placeholder "everything is `fade`" with real, verified filters: the actual `xfade`
transition catalogue (`fade`, `fadeblack`, `smoothleft`, `slideup`, `circleopen`, …), `zoompan`
push-in on accented clips, and a `setpts` speed accent. Each effect kind is smoke-tested against
real FFmpeg; any risky effect falls back to a clean hard cut rather than failing the render.

### 7. Deterministic fallback editor

If no codex/claude backend is available, or every agent call fails, the pipeline falls back to a
deterministic editor (rhythm grid + score-based selection using the existing drone-shot scores) so
it always produces a full-length edit offline. The fallback is clearly flagged in the report.

### 8. Integration & artifacts (`pipeline.py`)

Keep all audit artifacts and add agent-decision artifacts: `footage-ratings.json` (agent per-moment
ratings), `edit-decision.json` (agent's ordered edit + effect moments), the contact sheets on disk,
plus the existing `beat-plan.json`, `effect-plan.json`, timeline, and a `director-3-report.json`
summarising agent-vs-fallback, counts, and warnings. The codex location-title pipeline is unchanged.

## Data flow

`videos → keyframes/contact-sheets`; `music → beat grid`; `contact-sheets → agent ratings`;
`(ratings + music structure) → agent edit decision`; `edit decision + grid → Timeline`;
`Timeline → FFmpeg render + Resolve export`. JSON artifacts written at each stage.

## Tradeoffs (explicit — agent-driven)

- **Speed:** several vision calls per project (a few minutes), vs near-instant deterministic.
  Mitigated by contact-sheet batching (≤ ~15 calls), disk caching, and bounded sampling.
- **Non-deterministic:** same input can yield slightly different edits. Accepted (this is the point);
  the cached agent responses make a given run reproducible.
- **Requires an agent:** codex/claude must be on PATH; otherwise the deterministic fallback runs.
- **Cost/quota:** uses the local agent's quota.

## Testing

- **Deterministic units** (full coverage): contact-sheet tiling, beat grid fills the song, assembly
  invariants (no duplicate/adjacent-same/over-length), trim excludes edge zones, effect rendering
  smoke tests under real FFmpeg, fallback editor.
- **Agent boundary** (mock the runner, like `test_location.py`): prompt/schema construction, response
  parsing (valid, fenced, wrapped, malformed → safe fallback), and that ratings/edits flow into the
  timeline. The agent's *judgment* is not asserted (non-deterministic).
- **Real footage end-to-end** with actual codex on `Downloads\est`: length ≈ music, zero
  takeoff/landing in the timeline, varied non-repeating cuts, effects only at fitting peaks; render
  a preview and watch it.

## Out of scope

- Replacing librosa beat detection.
- True keyframed speed ramps (constant speed accent instead).
- Changes to the codex/claude location-title pipeline.
- Fine-tuning or training any model (we prompt the existing local agents).
