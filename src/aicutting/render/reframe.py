from aicutting.core.models import Timeline

# Social masters keyed by aspect ratio: the portrait reel (9:16) and the square feed post (1:1),
# both rendered at a 1080-wide master. "16:9" -- and anything unknown -- keeps the source-derived
# landscape master untouched, so the default cut stays byte-identical.
_SOCIAL_DIMENSIONS: dict[str, tuple[int, int]] = {
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
}
_DEFAULT_ASPECT = "16:9"
SUPPORTED_ASPECTS: tuple[str, ...] = (_DEFAULT_ASPECT, "9:16", "1:1")


def resolve_aspect(value: str) -> str:
    """Normalise a user-supplied aspect string; unknown values fall back to 16:9 landscape."""
    cleaned = value.strip().lower().replace(" ", "")
    if cleaned in _SOCIAL_DIMENSIONS or cleaned == _DEFAULT_ASPECT:
        return cleaned
    return _DEFAULT_ASPECT


def reframe_timeline(timeline: Timeline, aspect: str) -> Timeline:
    """Retarget a landscape timeline to a social aspect (9:16 reel, 1:1 square); 16:9 is unchanged.

    Only the output frame size changes -- the cut, clips, fps, grade and title are all preserved.
    The ffmpeg renderer cover-crops each landscape source into the new frame, so no pixels are
    stretched and there are no letterbox bars.
    """
    dimensions = _SOCIAL_DIMENSIONS.get(resolve_aspect(aspect))
    if dimensions is None:  # 16:9 / unknown -> keep the source-derived master untouched
        return timeline
    width, height = dimensions
    return timeline.model_copy(update={"width": width, "height": height})
