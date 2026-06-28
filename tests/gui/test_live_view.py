import json

from aicutting.core.progress import PipelinePhase
from aicutting.gui.live_view import live_view


def test_watch_surfaces_the_location_frame_and_place(tmp_path) -> None:  # type: ignore[no-untyped-def]
    shots = tmp_path / "location-screenshots"
    shots.mkdir()
    (shots / "0.jpg").write_bytes(b"x")
    (tmp_path / "location-suggestions.json").write_text(
        json.dumps([{"title": "Iceland", "place": "Iceland", "confidence": 0.97,
                     "should_render": True, "evidence": []}]),
        encoding="utf-8",
    )

    view = live_view(PipelinePhase.IDENTIFYING_LOCATION, tmp_path)

    assert view.hero.endswith("0.jpg")
    assert "Iceland" in view.detail


def test_direct_surfaces_contact_sheet_thumbnails_and_kept_count(tmp_path) -> None:  # type: ignore[no-untyped-def]
    sheets = tmp_path / "contact-sheets"
    sheets.mkdir()
    (sheets / "0.jpg").write_bytes(b"x")
    (sheets / "1.jpg").write_bytes(b"x")
    (tmp_path / "footage-ratings.json").write_text(
        json.dumps([{"keep": True}, {"keep": True}, {"keep": False}]), encoding="utf-8"
    )

    view = live_view(PipelinePhase.RATING_FOOTAGE, tmp_path)

    assert len(view.thumbnails) == 2
    assert "kept 2" in view.detail and "rejected 1" in view.detail


def test_cut_surfaces_the_chosen_clip_thumbnails(tmp_path) -> None:  # type: ignore[no-untyped-def]
    assets = tmp_path / "report-assets"
    assets.mkdir()
    (assets / "clip-00.jpg").write_bytes(b"x")

    view = live_view(PipelinePhase.RENDERING_FINAL_VIDEO, tmp_path)

    assert any(t.endswith("clip-00.jpg") for t in view.thumbnails)


def test_empty_output_dir_yields_an_empty_view(tmp_path) -> None:  # type: ignore[no-untyped-def]
    view = live_view(PipelinePhase.RATING_FOOTAGE, tmp_path)
    assert view.hero == "" and view.thumbnails == [] and view.detail == ""
