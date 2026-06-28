from dataclasses import dataclass

from aicutting.core.models import Timeline


@dataclass(frozen=True)
class LengthVariant:
    name: str  # used in the output filename: final-<name>.mp4
    seconds: float


# The social length masters rendered beside the full cut. A teaser is a quick hook; the short is a
# feed-length edit. Both are the *opening* of the full cut, so they keep the title reveal and stay
# beat-synced with the music from the top (an AI-picked mid-song highlight is the next refinement).
LENGTH_VARIANTS: tuple[LengthVariant, ...] = (
    LengthVariant("teaser", 15.0),
    LengthVariant("short", 60.0),
)


def opening_variant(timeline: Timeline, seconds: float) -> Timeline | None:
    """Return the opening ``seconds`` of ``timeline`` as a standalone cut, or None if not worth it.

    Every clip that starts before ``seconds`` is kept (so the variant runs to just past the mark on
    a clean clip boundary -- never a mid-clip chop). Returns None when the full cut already fits in
    ``seconds`` (no separate variant needed) or is too short to trim. The title, grade and frame
    format carry across unchanged; because it is the literal start of the beat-exact cut, it stays
    on the beat against the same music.
    """
    clips = timeline.clips
    if len(clips) < 2:
        return None
    kept = [clip for clip in clips if clip.timeline_start_s < seconds]
    if len(kept) < 2 or len(kept) == len(clips):
        return None
    span = round(kept[-1].timeline_start_s + kept[-1].timeline_duration_s, 3)
    return timeline.model_copy(update={"clips": kept, "target_duration_s": span})
