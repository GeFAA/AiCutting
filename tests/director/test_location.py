from aicutting.director.location import choose_renderable_title, fallback_location_suggestion
from aicutting.director.models import LocationSuggestion


def test_low_confidence_location_suggestion_is_not_renderable() -> None:
    suggestion = LocationSuggestion(
        title="Some Coast",
        place="unknown",
        confidence=0.4,
        evidence=["agent guess"],
        should_render=True,
    )

    assert choose_renderable_title([suggestion]) is None


def test_high_confidence_location_suggestion_becomes_title() -> None:
    suggestion = LocationSuggestion(
        title="Madeira Coast",
        place="Madeira, Portugal",
        confidence=0.86,
        evidence=["metadata GPS"],
        should_render=True,
    )

    title = choose_renderable_title([suggestion])

    assert title is not None
    assert title.title == "Madeira Coast"
    assert title.subtitle == "Madeira, Portugal"


def test_fallback_location_suggestion_is_safe_and_not_rendered() -> None:
    suggestion = fallback_location_suggestion("no metadata or agent backend available")

    assert suggestion.should_render is False
    assert suggestion.renderable is False
