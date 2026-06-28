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

## Shipped in 4.0

- ✅ **Motion-aware selection** — shaky / searching moments are dropped before the agent sees them.
- ✅ **Phrase-aware cutting** — cuts snap to downbeats and never run across a phrase boundary.
- ✅ **Cinematic colour grade** — a graded look on every clip, tunable per style.
- ✅ **Cross-clip colour matching** — every clip is nudged toward one consistent look.
- ✅ **Horizon levelling** — clips with a clearly tilted horizon are rotated back to level.
- ✅ **Speed ramps / slow-mo** — calm establishing shots drift in slow motion, still beat-exact.
- ✅ **Hero moment on the drop** — the clip on the biggest beat gets a pronounced push-in.
- ✅ **Musical-structure arc** — dynamic shots gravitate to the drops, establishing shots to the
  calm sections — within the colour journey.
- ✅ **Style presets** — `--style` cinematic · epic · chill · vlog retunes the whole edit.
- ✅ **Vertical & square masters** — `--aspect 9:16` / `1:1` reframes the cut into a full-bleed,
  cover-cropped social master (no bars, no stretch).
- ✅ **Content-aware reframe** — the vertical/square crop slides toward each clip's subject.
- ✅ **Length masters** — `--variants` renders a 15s teaser and a 60s short beside the full cut.
- ✅ **Self-critic** — the director grades its own finished cut (on-beat, variety, pacing) and
  surfaces the score in `report.html`.
- ✅ **Self-critic re-plan** — a weak cut is re-planned against the deterministic fallback and the
  better-grading one is kept.

## Still ahead

- Full optical stabilisation (shake, beyond horizon levelling — today shaky shots are rejected).
- True subject / saliency tracking for the reframe (faces, motion — beyond column detail).
- AI-picked mid-song highlight windows for the length masters (beyond the titled opening).
- Auto-pick the track by footage energy; cut-to-the-kick stem sync.
- A more polished desktop app.

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

## Milestones

| Theme | The win | Status |
|-------|---------|--------|
| Motion-aware rating | Drop shaky shots before the agent | ✅ shipped |
| Phrase-aware beat grid | Cut on downbeats, align to phrases | ✅ shipped |
| Cinematic colour grade | A graded look on every clip | ✅ shipped |
| Slow-mo speed ramps | Dreamy slow drift on the calm shots | ✅ shipped |
| Style presets | Epic / Chill / Vlog / Cinematic from one flag | ✅ shipped |
| Vertical / social reframe | 9:16 + 1:1 cover-cropped masters | ✅ shipped |
| Length variants | 15 s teaser + 60 s short | ✅ shipped |
| Self-critic grade | The director scores its own cut | ✅ shipped |
| Cross-clip colour matching | One consistent look across the film | ✅ shipped |
| Horizon levelling | Straighten tilted shots | ✅ shipped |
| Hero moment on the drop | Pronounced push-in on the biggest beat | ✅ shipped |
| Musical-structure arc | Dynamic on the drops, establishing on the calm | ✅ shipped |
| Self-critic re-plan loop | Keep the better-grading of two cuts | ✅ shipped |
| Content-aware reframe | Slide the crop toward the subject | ✅ shipped |
| Full optical stabilisation | Smooth out shake | next |
| Subject / saliency tracking | Faces & motion, beyond column detail | next |
| Auto-pick music + stem sync | Choose the track; cut to the kick | next |
| Polished desktop app | One-click preview & export | next |

---

## Why the rest is within reach

The groundwork for the remaining work already exists:

- The colour-journey sequencing already computes per-shot colour signatures — cross-clip colour
  matching extends them from *ordering* into *grading*.
- The motion / drone-shot analysis already scores smoothness and jitter per candidate —
  stabilisation and horizon levelling reuse those deterministic signals.
- The self-critic already grades each cut by dimension — the *re-plan* loop feeds the weakest
  stretch back into a re-cut.
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
