import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("PySide6") is None,
    reason="PySide6 is not installed",
)


def _load_widgets():
    pytest.importorskip("PySide6.QtWidgets")
    from aicutting.gui.widgets import PathPicker, StatusPanel

    return PathPicker, StatusPanel


def test_path_picker_constructs(qtbot) -> None:
    PathPicker, _ = _load_widgets()
    picker = PathPicker(label="Video folder", button_text="Choose")
    qtbot.addWidget(picker)

    assert picker.path() is None
    assert picker.label_text == "Video folder"


def test_status_panel_updates_message(qtbot) -> None:
    _, StatusPanel = _load_widgets()
    panel = StatusPanel()
    qtbot.addWidget(panel)

    panel.set_status("Analyzing footage")

    assert panel.current_message == "Analyzing footage"
