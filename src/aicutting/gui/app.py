import sys

from aicutting.gui.qt import require_qt


def main() -> int:
    qt = require_qt()
    from aicutting.gui.main_window import MainWindow

    app = qt.widgets.QApplication.instance() or qt.widgets.QApplication(sys.argv)
    app.setApplicationName("AiCutting Studio")
    window = MainWindow()
    window.resize(1100, 720)
    window.show()
    return int(app.exec())
