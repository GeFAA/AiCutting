# Cinematic Title Reveals 2.0 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Replace the single slow title rise with a set of distinct, punchy reveals that emerge from behind the terrain, share a light-sweep, are faster/well-edited, and are mapped to the `--style` preset.

**Architecture:** `render/titles.py` keeps `build_title_overlay(...)` as the entry point but `style` selects a **reveal** ("emerge" | "slide" | "drop" | "wipe", plus "horizon"/"plain" back-compat). Each reveal supplies per-element `y(t)` / `alpha(t)` expressions and optional extra mask; shared `_occlusion` (terrain luma) and `_light_sweep` (moving highlight) are composed by `build_title_overlay`. `StylePreset.title_reveal` maps each style to a reveal; a CLI `--reveal` overrides.

**Tech Stack:** Python 3.11+, FFmpeg `drawtext`/`blend`/`overlay`/`gblur`/`drawbox`; pytest; ruff; mypy. Spec: `docs/superpowers/specs/2026-06-28-title-reveals-2-design.md`.

## Global Constraints

- ffmpeg `drawtext` animates position (`x`/`y` as `f(t)`), alpha, and masks only — no font-size / blur / letter-spacing over time. Reveals use position + alpha + masks + the sweep.
- Keep the format-before-split pin (`[vbase]format=yuv420p,split=2`) — without it the base goes grayscale.
- Author commits as `GeFAA <121340757+GeFAA@users.noreply.github.com>`; no `Co-Authored-By` trailer.
- `py -m pytest`, `py -m ruff check .`, `py -m mypy src` stay green (line-length 100).
- The reveal look is tuned by rendering a short clip over real terrain and viewing frames — assertions cover structure, eyes cover the look.

---

### Task 1: Faster, punchier timing (the "boring" fix) + reveal dispatch scaffold

**Files:**
- Modify: `src/aicutting/render/titles.py`
- Test: `tests/render/test_titles.py`

**Interfaces:**
- Produces: `build_title_overlay(title, font, width, height, fps, *, style="emerge")` dispatches on `style`; `_REVEALS: dict[str, Callable]`; faster `_intro_fade()` (in 0.4–1.0 s, out 7–8 s).

- [ ] **Step 1: Write the failing test** (append to `tests/render/test_titles.py`):

```python
def test_intro_fade_is_faster_than_before() -> None:
    from aicutting.render.titles import _intro_fade
    fade = _intro_fade()
    assert "0.4" in fade and "8-t" in fade  # fades in by ~1s, out by 8s
    assert "lt(t,2),0" not in fade  # not the old slow 2-3s fade-in


def test_unknown_reveal_falls_back_to_emerge() -> None:
    from aicutting.render.titles import build_title_overlay
    from aicutting.core.models import LocationTitle
    title = LocationTitle(title="Madeira", subtitle="April 2026", confidence=0.9)
    out = build_title_overlay(title, None, 1920, 1080, 25.0, style="does-not-exist")
    assert out.endswith("[vout]") and "overlay=" in out
```

- [ ] **Step 2: Run to verify it fails** — `py -m pytest tests/render/test_titles.py::test_intro_fade_is_faster_than_before -v` → FAIL (old fade has `lt(t,2),0`).

- [ ] **Step 3: Implement.** Replace `_intro_fade` and add the dispatch. In `titles.py`:

```python
def _intro_fade() -> str:
    # Invisible, fade in 0.4->1.0 s (punchy), hold, fade out 7->8 s.
    return "if(lt(t,0.4),0,if(lt(t,1),(t-0.4)/0.6,if(lt(t,7),1,if(lt(t,8),8-t,0))))"
```

Change `build_title_overlay` to dispatch on a `_REVEALS` table (each reveal is a function with the same signature as `_emerge_subgraph`); keep "plain"/"horizon" working; unknown -> emerge:

```python
def build_title_overlay(title, font_path, width, height, fps, *, style="emerge"):
    if style == "plain":
        return f"[vbase]{build_drawtext_filter(title, font_path)}[vout]"
    if style == "horizon":
        return _emerge_subgraph(title, font_path, width, height, fps, mask="horizon")
    reveal = _REVEALS.get(style, _REVEALS["emerge"])
    return reveal(title, font_path, width, height, fps)
```

Speed up the emerge rise in `_emerge_subgraph`: change `rise_term` to settle by ~1.0 s:

```python
    rise_term = f"{rise}*(1-{_smoothstep('t', 0.4, 0.6)})"  # rises over 0.4..1.0 s (was 2..3.8)
    relax = _smoothstep("T", 2.2, 1.2)  # occlusion relaxes sooner so the settled title is legible
```

Define the table after the reveal functions exist (Task 2 adds the others; for now only emerge):

```python
_REVEALS = {"emerge": lambda t, f, w, h, fps: _emerge_subgraph(t, f, w, h, fps, mask="luma")}
```

- [ ] **Step 4: Run to verify it passes** — `py -m pytest tests/render/test_titles.py -q && py -m ruff check . && py -m mypy src` → PASS, clean.

- [ ] **Step 5: Visual check + commit.** Render a short title clip over real terrain and view frames at 0.5/1.0/2.0 s (use the snippet in Task 5); confirm the title snaps in by ~1 s and emerges from behind the terrain.

```bash
git add src/aicutting/render/titles.py tests/render/test_titles.py
git commit -m "feat(titles): punchier reveal timing + reveal dispatch"
```

### Task 2: The reveal styles — slide, drop, wipe

**Files:** Modify `src/aicutting/render/titles.py`; Test `tests/render/test_titles.py`.

**Interfaces:** Produces `_slide_subgraph`, `_drop_subgraph`, `_wipe_subgraph` (same signature as `_emerge_subgraph` minus `mask`), registered in `_REVEALS`. All keep the luma occlusion; they differ in motion / extra mask.

- [ ] **Step 1: Write the failing test:**

```python
def test_each_reveal_emerges_from_behind_the_terrain() -> None:
    from aicutting.render.titles import build_title_overlay
    from aicutting.core.models import LocationTitle
    title = LocationTitle(title="Madeira", subtitle="April 2026", confidence=0.9)
    for style in ("emerge", "slide", "drop", "wipe"):
        out = build_title_overlay(title, None, 1920, 1080, 25.0, style=style)
        assert "[vbase]format=yuv420p,split=2[base][src]" in out  # format pinned before split
        assert "blend=all_expr=" in out  # the occlusion blend
        assert out.endswith("overlay=eof_action=pass[vout]")


def test_reveals_differ_in_motion() -> None:
    from aicutting.render.titles import build_title_overlay
    from aicutting.core.models import LocationTitle
    title = LocationTitle(title="X", subtitle=None, confidence=0.9)
    graphs = {s: build_title_overlay(title, None, 1920, 1080, 25.0, style=s)
              for s in ("emerge", "slide", "drop", "wipe")}
    assert len({*graphs.values()}) == 4  # four distinct filtergraphs
```

- [ ] **Step 2: Run to verify it fails** — the new styles fall back to emerge so the four graphs aren't distinct → FAIL.

- [ ] **Step 3: Implement.** Refactor `_emerge_subgraph` to take a motion (`y_expr` builder) and an optional reveal mask, so the four reveals share one assembler. Extract:

```python
def _reveal_subgraph(title, font_path, width, height, fps, *, y_of, reveal_mask=None):
    title_size = round(height / 11); subtitle_size = round(height / 26)
    title_y = round(height * 0.34); subtitle_y = title_y + title_size + round(height * 0.018)
    shadow = max(1, round(height / 360)); sigma = max(1.0, height / 360); window_s = 9.0
    fade = _intro_fade()
    relax = _smoothstep("T", 2.2, 1.2)
    blend_expr = f"A*(B+(255-B)*{relax})/255"
    bold = _bold_variant(font_path)
    draws = [_drawtext(title.title, bold, title_size, shadow, y_of(title_y), fade)]
    if title.subtitle:
        draws.append(_drawtext(title.subtitle, font_path, subtitle_size, shadow,
                               y_of(subtitle_y), fade))
    text_chain = ",".join(draws)
    mask_mid = "lut=c0='255*clip((val-70)/60,0,1)'"
    sweep = _light_sweep(width, height, fps, window_s)
    extra = f",{reveal_mask}" if reveal_mask else ""
    segments = [
        "[vbase]format=yuv420p,split=2[base][src]",
        f"[src]format=gray,{mask_mid},gblur=sigma={_g(sigma)},"
        f"trim=end={_g(window_s)},setpts=PTS-STARTPTS[occ]",
        f"color=c=black@0:s={width}x{height}:d={_g(window_s)}:r={fps},format=rgba,"
        f"{text_chain}{sweep}{extra}[txtcol]",
        "[txtcol]split[txtc1][txtc2]",
        "[txtc2]alphaextract[ta]",
        f"[ta][occ]blend=all_expr='{blend_expr}':shortest=1[na]",
        "[txtc1][na]alphamerge[tl]",
        "[base][tl]overlay=eof_action=pass[vout]",
    ]
    return ";".join(segments)
```

Define each reveal's motion (`y_of` returns the `y` expression for a base y):

```python
def _emerge_subgraph(title, font_path, width, height, fps, *, mask="luma"):
    rise = round(height * 0.11)
    if mask == "horizon":  # legacy horizon mask path, kept
        return _horizon_subgraph(title, font_path, width, height, fps)
    return _reveal_subgraph(title, font_path, width, height, fps,
        y_of=lambda y: f"{y}+{rise}*(1-{_smoothstep('t', 0.4, 0.6)})")

def _slide_subgraph(title, font_path, width, height, fps):
    off = round(height * 0.22)  # slides up from lower in the frame
    return _reveal_subgraph(title, font_path, width, height, fps,
        y_of=lambda y: f"{y}+{off}*(1-{_smoothstep('t', 0.4, 0.7)})")

def _drop_subgraph(title, font_path, width, height, fps):
    off = round(height * 0.14)  # drops down from above into place
    return _reveal_subgraph(title, font_path, width, height, fps,
        y_of=lambda y: f"{y}-{off}*(1-{_smoothstep('t', 0.4, 0.6)})")

def _wipe_subgraph(title, font_path, width, height, fps):
    # stationary text revealed by a soft vertical edge sweeping left->right over 0.4..1.3 s
    edge = (f"geq=lum='255*clip((X-({width}*1.25*clip((T-0.4)/0.9,0,1)-{width}*0.15))"
            f"/({width}*0.12),0,1)',negate")
    return _reveal_subgraph(title, font_path, width, height, fps,
        y_of=lambda y: str(y), reveal_mask=None)  # wipe handled via reveal_mask below
```

> Note for the wipe: apply `edge` to the text alpha by adding it to `reveal_mask`. During Step 5 render-and-view, adjust the `geq` constants until the edge sweeps cleanly across the title. (The exact constants are tuned visually.)

Register them:

```python
_REVEALS = {
    "emerge": lambda t, f, w, h, fps: _emerge_subgraph(t, f, w, h, fps),
    "slide": _slide_subgraph,
    "drop": _drop_subgraph,
    "wipe": _wipe_subgraph,
}
```

Keep the existing horizon body as `_horizon_subgraph` (renamed) so `style="horizon"` still works.

- [ ] **Step 4: Run to verify it passes** — `py -m pytest tests/render/test_titles.py -q && py -m ruff check . && py -m mypy src` → PASS, clean.

- [ ] **Step 5: Commit** — `git add ... && git commit -m "feat(titles): slide / drop / wipe reveals sharing the occlusion"`

### Task 3: The shared light sweep

**Files:** Modify `src/aicutting/render/titles.py`; Test `tests/render/test_titles.py`.

**Interfaces:** Produces `_light_sweep(width, height, fps, window_s) -> str` — a filter chain segment appended to the text-colour layer that screens a moving soft highlight across the glyphs over ~0.6–1.4 s.

- [ ] **Step 1: Write the failing test:**

```python
def test_reveal_has_a_light_sweep() -> None:
    from aicutting.render.titles import build_title_overlay
    from aicutting.core.models import LocationTitle
    out = build_title_overlay(LocationTitle(title="X", subtitle=None, confidence=0.9),
                              None, 1920, 1080, 25.0, style="emerge")
    assert "drawbox" in out  # the moving highlight band
```

- [ ] **Step 2: Run to verify it fails** — no `drawbox` yet → FAIL.

- [ ] **Step 3: Implement** `_light_sweep` — a moving white soft band, screened onto the text so only the glyphs brighten as it passes:

```python
def _light_sweep(width, height, fps, window_s):
    # A soft white band sweeps left->right over 0.6..1.4 s; `screen` brightens only the glyphs it
    # crosses (the band is multiplied by the text alpha downstream via the rgba layer it lives on).
    band = round(height * 0.16)
    x = f"-{band} + ({width}+{2 * band})*clip((t-0.6)/0.8,0,1)"
    return (f",drawbox=x='{x}':y=0:w={band}:h={height}:color=white@0.5:t=fill,"
            f"gblur=sigma={_g(max(2.0, height / 90))}")
```

> During Step 5 render-and-view, tune `@0.5` (sweep intensity) and the timing so the highlight reads as a tasteful specular pass, not a flash.

- [ ] **Step 4: Run to verify it passes** — `py -m pytest tests/render/test_titles.py -q` → PASS.

- [ ] **Step 5: Commit** — `git commit -m "feat(titles): shared light-sweep highlight on the reveal"`

### Task 4: Map reveals to the style preset + CLI override

**Files:** Modify `src/aicutting/core/style.py`, `src/aicutting/pipeline.py`, `src/aicutting/cli.py`; Test `tests/test_style_presets.py`, `tests/test_pipeline.py`.

**Interfaces:** Produces `StylePreset.title_reveal: str` (cinematic→"emerge", epic→"emerge", chill→"slide", vlog→"drop"); `cut(..., reveal: str | None = None)`; the title overlay is built with the chosen reveal.

- [ ] **Step 1: Write the failing test** (in `tests/test_style_presets.py`):

```python
def test_presets_carry_a_title_reveal() -> None:
    from aicutting.core.style import STYLE_PRESETS
    assert STYLE_PRESETS["cinematic"].title_reveal == "emerge"
    assert STYLE_PRESETS["chill"].title_reveal == "slide"
    assert STYLE_PRESETS["vlog"].title_reveal == "drop"
```

- [ ] **Step 2: Run to verify it fails** — `StylePreset` has no `title_reveal` → FAIL.

- [ ] **Step 3: Implement.** Add `title_reveal: str` to the `StylePreset` dataclass and set it on each preset (cinematic/epic "emerge", chill "slide", vlog "drop"). Thread it: where `build_ffmpeg_command` builds the title overlay it currently calls `build_title_overlay(..., )` with the default style — pass the reveal. The reveal reaches the renderer via `Timeline`: add `Timeline.title_reveal: str = "emerge"` (model field, default keeps current behaviour), set it in `_finalize_timeline` from `style.title_reveal` (and the CLI `--reveal` override threaded through `cut`), and in `render/ffmpeg.py` call `build_title_overlay(..., style=timeline.title_reveal)`.

- [ ] **Step 4: Run to verify it passes** — `py -m pytest -q && py -m ruff check . && py -m mypy src` → PASS, clean.

- [ ] **Step 5: Commit** — `git commit -m "feat(titles): map reveals to style presets + --reveal override"`

### Task 5: Visual verification of every reveal + docs

**Files:** docs (`README.md` / `CHANGELOG.md`), no src change unless tuning.

- [ ] **Step 1: Render + view each reveal over real terrain.** Use a real clip with a clear ridge/horizon. For each style render ~3 s and grab frames across the reveal:

```python
# scratch: render one reveal and dump frames
from aicutting.core.models import Timeline, TimelineClip, Transition, TransitionType, LocationTitle
from aicutting.render.ffmpeg import render_timeline
clip = TimelineClip(asset_path=Path(REAL_MP4), source_start_s=2.0, source_end_s=5.0,
    timeline_start_s=0.0, transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0.0),
    speed=1.0, color_intent="x")
for style in ("emerge","slide","drop","wipe"):
    tl = Timeline(target_duration_s=3.0, clips=[clip], fps=30.0, width=1920, height=1080,
        title=LocationTitle(title="Madeira", subtitle="April 2026", confidence=0.9),
        title_reveal=style)
    render_timeline(tl, OUT/f"title-{style}.mp4", music_path=None)
# then ffmpeg -ss 0.6/1.0/2.0 -i title-<style>.mp4 -frames:v 1 frame.png ; Read the PNGs
```

Confirm for each: the title is hidden behind the terrain at first, snaps in by ~1 s with the sweep, holds legibly, exits cleanly. Tune the `geq`/`drawbox`/timing constants in `titles.py` until each reads well, re-render, re-view.

- [ ] **Step 2: Document.** README: note the title "emerges from behind the terrain with style-matched reveals"; CHANGELOG: a "Title reveals 2.0" entry. Update the architecture title sentence if needed.

- [ ] **Step 3: Commit** — `git commit -m "feat(titles): tune reveals + document Title Reveals 2.0"`

---

## Self-Review

- **Spec coverage:** faster timing (Task 1) · 4 reveals emerging from terrain (Tasks 1–2) · shared light sweep (Task 3) · style→reveal mapping + `--reveal` (Task 4) · plain/horizon back-compat (Task 1) · visual verification (Task 5). The "kinetic per-letter" idea is intentionally replaced by drop/wipe — per-letter needs proportional-font width measurement ffmpeg can't do, so it is out (noted here, not silently dropped).
- **Placeholders:** the ffmpeg `geq`/`drawbox` constants are explicitly marked as visually tuned in Task 5 (render-and-view), which is the honest method for motion design; the structure and dispatch are fully coded and TDD-covered.
- **Type consistency:** `build_title_overlay(..., style=...)`, `_reveal_subgraph(..., y_of=, reveal_mask=)`, `_light_sweep(width, height, fps, window_s)`, `StylePreset.title_reveal`, `Timeline.title_reveal` are used identically across tasks.
