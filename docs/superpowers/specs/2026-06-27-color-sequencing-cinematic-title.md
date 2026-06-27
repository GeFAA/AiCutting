# Color-coherent sequencing + cinematic title reveal

**Goal:** The montage should travel through visually-coherent groups (e.g. all the
black lava-field shots together, then flow into the green/moss shots) instead of
jumping between scene types, and the location/date title should reveal cinematically
— ideally appearing *from behind* the terrain (a mountain/ridge in the intro shot)
rather than as a flat overlay.

## A. Color-coherent sequencing

**Problem:** clips are ordered by the agent edit + beat grid, so lava and green
shots interleave ("vermischt"). The user wants contiguous color groups in a journey.

**Approach (deterministic; the vision agent still rates/rejects + finds the location):**
1. `analysis/color.py` — for every kept moment, extract one frame with cv2 and
   compute a small color signature: greenness (fraction of vivid green-hue pixels),
   plus mean brightness and saturation. Returns `dict[moment_id, ColorSignature]`.
2. `planning/sequence.py` — order the kept moments into a coherent sequence by the
   color signature (primary axis = greenness ascending: dark lava → green), so
   similar-colored shots are contiguous. Keep a light secondary sort (brightness)
   for stability.
3. Assembly fills the beat grid **in that color order** — slot i takes the next
   moment in the sequence (reusing within the current color neighbourhood when the
   grid needs more clips than moments). Energy still drives clip *length* (calm =
   long, drops = fast) and the on-beat guarantee is unchanged.
4. Pipeline wires it in (replaces the agent's per-slot ordering with the
   color-ordered fill); the report shows the color groups.

**Acceptance:** consecutive clips share a color neighbourhood (no lava→green→lava
thrash); the cut still lands 40/40 on the beat; all source files still used.

## B. Cinematic title reveal

**Problem:** the title is a flat lower-third. The user wants it to appear *behind*
the terrain, very professional.

**Approach:**
1. Prototype an ffmpeg filtergraph (sub-agent) that makes a text overlay appear to
   rise from behind the landscape on a real Iceland clip: a luma mask so the dark
   foreground terrain occludes the text (text shows over the bright sky and is
   hidden by the dark ridge), combined with a slow rise + fade. Robust fallback: a
   rise-from-the-horizon-line mask + fade if luma masking is unreliable on a shot.
2. Choose the intro shot to favour the effect (clear horizon, dark foreground ridge,
   bright sky).
3. Integrate into `render/titles.py` + `render/ffmpeg.py` (the title is drawn on the
   composited base, so the mask is derived from the intro segment), preserving the
   existing fps-match + xfade chain. Keep the plain faded lower-third as a fallback.

**Acceptance:** on the rendered video the title visibly emerges from behind the
terrain (verified by extracting frames across the reveal), reads cleanly, and the
render stays green (no ffmpeg errors, cuts still on the beat).

## Constraints
TDD where unit-testable (color signature, sequence order, filter-string shape);
real ffmpeg smoke renders + frame inspection for the visual parts. ruff/mypy clean.
No questions to the user — resolve uncertainties with sub-agents.
