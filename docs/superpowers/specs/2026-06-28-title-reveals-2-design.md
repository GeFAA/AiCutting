# Cinematic Title Reveals 2.0 — design

**Date:** 2026-06-28
**Area:** `render/titles.py` (the location/date title overlay).

## Goal

The current title reveal is a single slow rise + fade (~6 s on screen) — passive and a bit boring.
Rework it into a small set of **distinct, punchy, well-edited reveals** that still emerge from behind
the terrain, feel premium ("krass"), and vary automatically so a run never looks templated.

## Constraints (what ffmpeg `drawtext` can and can't do)

`drawtext` animates **position** (`x`/`y` as `f(t)`), **alpha** (fade), and we can mask the text with
**video luma** (the terrain occlusion) or a **moving mask** (a wipe). It does **not** animate font
size, letter-spacing, or blur over time. So the reveal toolkit is: position moves, per-element/-letter
alpha, terrain occlusion, a moving **light sweep** highlight, and **mask wipes** — used boldly with
fast, confident timing. No fake scale/blur.

## The reveals

A `reveal` selects the style; all keep the **luma terrain occlusion** (the title rises out from
behind the dark foreground) as the shared signature, plus a shared **light-sweep** highlight that
travels across the glyphs as the title settles, and a clean **slide-back / fade** exit.

- **emerge** (hero, the improved default) — the title rises out from behind the ridge faster than
  before (settled by ~1.0 s, not ~1.8 s) with a small overshoot-and-settle, the light sweep crosses
  as it lands, holds confidently, then slides back down behind the terrain on the way out.
- **kinetic** — the letters stagger in left-to-right (each rises + fades a beat after the last),
  occluded by the terrain — energetic, editorial.
- **wipe** — a soft-edged vertical light edge sweeps across and reveals the glyphs as it passes
  (over the occlusion), like a reveal wipe.
- **slide** — the block slides up from the lower third into place (occluded), gentle and elegant.

Timing for all: invisible → reveal completes by ~1.2 s → confident hold → graceful exit by ~7 s
(window ~8–9 s). Faster and more deliberate than the current 2–3.8 s rise.

## Variety — mapped to the style preset

The pipeline maps each `--style` to a fitting reveal, so variety and an "edited" feel come for free:

| `--style` | reveal |
|-----------|--------|
| cinematic | emerge |
| epic | emerge (stronger sweep, fastest) |
| chill | slide |
| vlog | kinetic |

A new `StylePreset.title_reveal` field carries this. An optional CLI `--reveal emerge|kinetic|wipe|slide`
overrides it. The luma-vs-horizon mask choice and the `plain` fallback stay.

## Architecture

`build_title_overlay(title, font, w, h, fps, *, style="emerge")` stays the entry point but `style`
becomes the reveal name (back-compat: "emerge"/"horizon"/"plain" keep working; new names add styles).
Internally:

- `_text_layer(...)` — builds the `drawtext` chain (shared), parameterised by the per-element
  `y(t)` and `alpha(t)` expressions so each reveal supplies its own motion.
- `_light_sweep(w, h, fps)` — a moving highlight layer blended onto the text alpha (the premium
  touch), shared by all reveals.
- `_occlusion(...)` — the existing luma/horizon terrain mask (kept).
- One small function per reveal returns the per-element `(y_expr, alpha_expr)` and any extra mask
  (the wipe); `build_title_overlay` assembles layer → sweep → occlusion → overlay.

This keeps each reveal a small, testable unit and the shared pieces DRY.

## Testing

- Unit tests on the filter strings: each reveal name produces a valid subgraph consuming `[vbase]`
  and producing `[vout]`; the sweep and occlusion appear; `plain` still returns the flat lower-third;
  unknown names fall back to `emerge`. The existing title tests (drawtext present, format pinned
  before split, `overlay=...[vout]`) stay green.
- `StylePreset.title_reveal` mapping is unit-tested; the cinematic default stays byte-identical only
  where unchanged (the reveal itself is intentionally new).
- **Visual verification:** render a short clip with each reveal over real terrain and extract frames
  across the reveal (≈0.4 s, 1.0 s, 2.0 s, exit) to confirm each reads as intended and the title
  emerges from behind the terrain. (Snapshots reviewed, not just asserted.)

## Out of scope (YAGNI)
Per-clip lower-thirds / multiple captions, 3D text, font downloads, beat-locked reveal timing
(could be a follow-up: pass the first downbeat as the reveal start).
