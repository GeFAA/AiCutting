from dataclasses import dataclass
from types import ModuleType


@dataclass(frozen=True)
class QtModules:
    core: ModuleType
    gui: ModuleType
    widgets: ModuleType


def require_qt() -> QtModules:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "AiCutting Studio requires PySide6. Install the GUI extra with: "
            'py -m pip install -e ".[gui]"'
        ) from exc
    return QtModules(core=QtCore, gui=QtGui, widgets=QtWidgets)
