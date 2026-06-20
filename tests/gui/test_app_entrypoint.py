import builtins

import pytest

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
