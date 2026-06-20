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


def _load_main_window():
    pytest.importorskip("PySide6.QtWidgets")
    from aicutting.gui.main_window import MainWindow

    return MainWindow


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


def test_main_window_constructs(qtbot) -> None:
    MainWindow = _load_main_window()
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "AiCutting Studio"
    assert window.start_button.isEnabled() is False
