import sys
from pathlib import Path

from aicutting.gui.qt import require_qt

_QML_DIR = Path(__file__).parent / "qml"
_QML_MAIN = _QML_DIR / "Main.qml"


def main() -> int:
    qt = require_qt()
    from PySide6.QtQml import QQmlApplicationEngine

    from aicutting.gui.backend import Backend

    app = qt.gui.QGuiApplication.instance() or qt.gui.QGuiApplication(sys.argv)
    app.setApplicationName("AiCutting Studio")
    backend = Backend()
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(_QML_DIR))
    engine.rootContext().setContextProperty("backend", backend)
    engine.load(str(_QML_MAIN))
    if not engine.rootObjects():
        return 2
    return int(app.exec())


def main_widgets() -> int:
    # The legacy QWidgets window, kept until the QML View reaches parity.
    qt = require_qt()
    from aicutting.gui.main_window import MainWindow

    app = qt.widgets.QApplication.instance() or qt.widgets.QApplication(sys.argv)
    app.setApplicationName("AiCutting Studio")
    window = MainWindow()
    window.resize(1100, 720)
    window.show()
    return int(app.exec())


def main_cli() -> int:
    try:
        return main()
    except RuntimeError as exc:
        print(str(exc))
        return 2
