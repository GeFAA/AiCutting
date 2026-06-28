import builtins
import tomllib
from pathlib import Path

import pytest

import aicutting.gui.app as gui_app
from aicutting.gui.qt import require_qt


def test_require_qt_raises_friendly_error_when_pyside6_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("PySide6"):
            raise ModuleNotFoundError("No module named 'PySide6'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError, match="Install the GUI extra"):
        require_qt()


def test_main_cli_returns_friendly_error_when_gui_extra_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_main() -> int:
        raise RuntimeError("Install the GUI extra")

    monkeypatch.setattr(gui_app, "main", fake_main)

    result = gui_app.main_cli()

    assert result == 2
    assert "Install the GUI extra" in capsys.readouterr().out


def test_qml_main_file_exists_and_references_backend() -> None:
    qml = Path("src/aicutting/gui/qml/Main.qml").read_text(encoding="utf-8")
    assert "backend" in qml  # the View binds to the Backend context property


def test_desktop_script_uses_cli_wrapper() -> None:
    project_root = Path(__file__).parents[2]
    pyproject = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["aicutting-studio"] == "aicutting.gui.app:main_cli"
