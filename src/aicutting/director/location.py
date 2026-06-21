from aicutting.core.models import LocationTitle
from aicutting.director.models import LocationSuggestion


def choose_renderable_title(suggestions: list[LocationSuggestion]) -> LocationTitle | None:
    renderable = [suggestion for suggestion in suggestions if suggestion.renderable]
    if not renderable:
        return None
    best = max(renderable, key=lambda suggestion: suggestion.confidence)
    return LocationTitle(title=best.title, subtitle=best.place, confidence=best.confidence)


def fallback_location_suggestion(reason: str) -> LocationSuggestion:
    return LocationSuggestion(
        title="",
        place="unknown",
        confidence=0.0,
        evidence=[reason],
        should_render=False,
    )
