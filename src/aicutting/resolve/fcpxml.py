from xml.etree.ElementTree import Element, SubElement, tostring

from aicutting.core.models import Timeline


def timeline_to_fcpxml(timeline: Timeline) -> str:
    fcpxml = Element("fcpxml", version="1.10")
    resources = SubElement(fcpxml, "resources")
    project = SubElement(fcpxml, "project", name="AiCutting")
    sequence = SubElement(
        project,
        "sequence",
        duration=f"{timeline.target_duration_s}s",
        format="r1",
    )
    spine = SubElement(sequence, "spine")

    SubElement(
        resources,
        "format",
        id="r1",
        name="AiCuttingFormat",
        frameDuration=f"1/{int(round(timeline.fps))}s",
        width=str(timeline.width),
        height=str(timeline.height),
    )

    asset_ids: dict[str, str] = {}
    for index, clip in enumerate(timeline.clips, start=1):
        key = str(clip.asset_path)
        asset_id = asset_ids.setdefault(key, f"asset{index}")
        if asset_id == f"asset{index}":
            SubElement(
                resources,
                "asset",
                id=asset_id,
                src=clip.asset_path.as_posix(),
                name=clip.asset_path.name,
            )
        SubElement(
            spine,
            "asset-clip",
            ref=asset_id,
            name=clip.asset_path.name,
            offset=f"{clip.timeline_start_s}s",
            start=f"{clip.source_start_s}s",
            duration=f"{clip.timeline_duration_s}s",
        )

    return tostring(fcpxml, encoding="unicode") + "\n"
