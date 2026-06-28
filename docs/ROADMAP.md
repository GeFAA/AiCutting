# AI Drone Director — 4.0 Roadmap

**3.0 produces a clean, beat-synced, colour-coherent cinematic cut. 4.0 makes it feel
hand-crafted by a pro editor** — judgment that understands motion, edits that follow the
song's story, real colour, and a master for every screen. Local-first and transparent,
always.

---

## Where we are — 3.0

- A vision agent rates every sampled moment, **rejects landings, takeoffs and filler**, and
  keeps only sharp, well-composed shots with real depth.
- Cuts land **exactly on the beat**; pacing follows the music's energy (calm shots breathe,
  drops cut fast).
- A **colour-coherent journey** orders the shots (dark lava grouped first, flowing into the
  green) instead of jumping between scene types.
- A **cinematic title emerges from behind the terrain** — the location is recognised from the
  scenery and the date is read from the footage metadata.
- Directional push-ins, cohesive crossfades, and **full transparency**: a `report.html` of
  every decision, a live progress view, and a one-command, 100% local pipeline.

---

## Shipped in 4.0 so far

- ✅ **Cinematic colour grade** — a graded look on every clip, tunable per style.
- ✅ **Motion-aware selection** — shaky / searching moments are dropped before the agent sees them.
- ✅ **Phrase-aware cutting** — cuts snap to downbeats and never run across a phrase boundary.
- ✅ **Speed ramps / slow-mo** — calm establishing shots drift in slow motion, still beat-exact.
- ✅ **Style presets** — `--style` cinematic · epic · chill · vlog retunes the whole edit.
- ✅ **Vertical & square masters** — `--aspect 9:16` / `1:1` reframes the cut into a full-bleed,
  cover-cropped social master (no bars, no stretch). *Subject-aware tracking is the next step.*

---

## 4.0 pillars

### 1 · It watches motion, not just frames
Today the agent judges single thumbnails. 4.0 judges **movement**.
- **Multi-frame / short-clip rating** so the agent sees how a shot moves.
- An **optical-flow stability score** — reject shake and drift, prefer smooth reveals.
- **Robust landing / takeoff detection** from descent motion, not just edge-trimming.

### 2 · The edit follows the song's story
- **Musical-structure detection** (intro · build · drop · breakdown · outro).
- The **edit arc maps to the structure**: establish in the intro, accelerate into the drop,
  land the hero shot *on* the drop, breathe in the breakdown.
- **Phrase-aware cutting** — cut harder on phrase boundaries, micro-cuts on builds.

### 3 · Real colour, not just order
- **Auto white-balance + a cinematic grade** (LUT), not only sequencing.
- **Cross-clip colour matching** for one consistent look across the whole film.
- Optional **per-section grades** that evolve with the journey.

### 4 · Craft
- **Stabilisation + automatic horizon levelling** (the agent already rejects tilt — now fix it).
- **Hero-shot detection** + tasteful **speed ramps / slow-mo** on the standout moment.
- **Content-aware, motion-matched transitions** (whip pans that follow the camera move,
  match cuts, light leaks) — still cohesive and beat-safe.

### 5 · Delivery for every screen
- **Subject-aware auto-reframe** to 9:16 and 1:1 for social.
- **4K / HDR**, chapter markers, and **multiple length variants** (15 s teaser · 60 s · full).

### 6 · Make it yours
- **Style presets** — Epic · Chill · Travel Vlog · Hyperlapse — that tune pacing, grade,
  transitions and title style.
- **Bring-your-own music** or auto-pick a track by footage energy; **cut-to-the-kick** stem sync.
- A **polished desktop app**: drop a folder, pick a style and a song, watch the live progress,
  preview, export.

### 7 · Self-improving
- An **auto-critic** scores the finished edit (pacing, variety, on-beat, colour) and re-plans
  the weak parts — the director reviews its own work.

---

## Proposed milestones

| Release | Theme | The win |
|--------|-------|---------|
| **4.0** | Motion-aware rating + musical-structure arc | The two biggest quality jumps |
| **4.1** | Colour grading + stabilisation / levelling | A consistent, polished look |
| **4.2** | Hero moments + speed ramps + richer transitions | Cinematic punch |
| **4.3** | Vertical / social reframe + length variants | Ready for every platform |
| **4.4** | Style presets + polished app | One-click, your style |
| **4.5** | Self-critic quality loop | It grades and fixes itself |

---

## Why 4.0 is within reach

Much of the groundwork already exists in 3.0 and is waiting to be wired in:

- The motion / drone-shot analysis already scores smoothness, jitter, search-flight and
  takeoff/landing per candidate — pillar 1 feeds those deterministic signals into selection.
- Beat analysis already detects downbeats and phrase boundaries — pillar 2 snaps the arc to them.
- Per-shot colour signatures already exist — pillar 3 extends them from *ordering* into *grading*.
- A single cached decode pass (today clips are re-opened for keyframes, contact sheets, colour
  signatures, report thumbnails and the render) is a large performance win that unblocks the
  heavier passes above.

---

## Engineering principles (unchanged)

- **Local-first** — vision agent (codex / claude) + ffmpeg, no cloud upload required.
- **Beat-exact** — every new feature preserves the on-the-beat guarantee.
- **Transparent** — every decision stays visible in `report.html`.
- **Graceful** — each pillar ships behind the existing deterministic fallbacks, so a run never
  breaks when the agent or a model is unavailable.
