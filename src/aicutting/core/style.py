"""Style presets that retune the whole edit (pace, slow-mo, transitions, grade).

The default ``cinematic`` preset holds the exact values the pipeline shipped with, so selecting it
(the default everywhere) reproduces the original behaviour byte-for-byte. The other presets nudge
the four knobs the pipeline exposes:

* ``pace`` — multiplier on the calm/mid rhythm spans (``planning.rhythm.build_rhythm_grid``).
  ``> 1`` lengthens the holds (slower cutting); ``< 1`` shortens them (punchier cutting); ``1.0``
  keeps the cinematic spans. The spans stay whole-bar multiples so the downbeat snapping holds.
* ``slow_mo_speed`` / ``slow_mo_energy`` — the dreamy slow drift on calm slots
  (``planning.assemble.assemble_cut_plan``). ``slow_mo_speed = 1.0`` disables slow-mo entirely.
* ``transition_energy`` — crossfades are added on hard-cut slots quieter than this energy; ``0.0``
  forces all hard cuts.
* ``grade_strength`` — intensity of the cinematic colour grade (``render.ffmpeg``); ``1.0`` is the
  cinematic grade, ``0.0`` is neutral.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class StylePreset:
    name: str
    pace: float
    slow_mo_speed: float
    slow_mo_energy: float
    transition_energy: float
    grade_strength: float


STYLE_PRESETS: dict[str, StylePreset] = {
    # The shipped values: cinematic is a no-op that reproduces the original cut exactly.
    "cinematic": StylePreset(
        name="cinematic",
        pace=1.0,
        slow_mo_speed=0.75,
        slow_mo_energy=0.3,
        transition_energy=0.4,
        grade_strength=1.0,
    ),
    # Punchier holds, deeper slow-mo contrast, a touch more crossfades, a stronger grade.
    "epic": StylePreset(
        name="epic",
        pace=0.8,
        slow_mo_speed=0.6,
        slow_mo_energy=0.35,
        transition_energy=0.45,
        grade_strength=1.4,
    ),
    # Longer calm holds and a softer grade; otherwise the gentle cinematic feel.
    "chill": StylePreset(
        name="chill",
        pace=1.4,
        slow_mo_speed=0.75,
        slow_mo_energy=0.3,
        transition_energy=0.4,
        grade_strength=0.6,
    ),
    # Fast, punchy hard cuts: no slow-mo, no crossfades, a near-neutral grade.
    "vlog": StylePreset(
        name="vlog",
        pace=0.7,
        slow_mo_speed=1.0,
        slow_mo_energy=0.3,
        transition_energy=0.0,
        grade_strength=0.2,
    ),
}


def resolve_style(name: str) -> StylePreset:
    """Return the preset for ``name`` (case-insensitive); unknown names fall back to cinematic."""
    return STYLE_PRESETS.get(name.strip().lower(), STYLE_PRESETS["cinematic"])
