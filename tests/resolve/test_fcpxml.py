import xml.etree.ElementTree as ET
from pathlib import Path

from aicutting.core.models import Timeline, TimelineClip, Transition, TransitionType
from aicutting.resolve.fcpxml import timeline_to_fcpxml


def test_timeline_to_fcpxml_is_parseable() -> None:
    timeline = Timeline(
        target_duration_s=4,
        fps=25,
        width=1920,
        height=1080,
        clips=[
            TimelineClip(
                asset_path=Path("clip.mp4"),
                source_start_s=0,
                source_end_s=4,
                timeline_start_s=0,
                transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0),
                speed=1,
                color_intent="subtle_cinematic",
            )
        ],
    )

    xml_text = timeline_to_fcpxml(timeline)

    root = ET.fromstring(xml_text)
    assert root.tag == "fcpxml"
    assert root.find(".//asset") is not None
