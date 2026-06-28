import subprocess
import sys
import textwrap


def test_main_qml_loads_in_every_state() -> None:
    # Load Main.qml under each backend status in an isolated offscreen process, so a QML syntax or
    # binding error fails the build. The software backend needs no GPU; offscreen needs no display.
    code = textwrap.dedent(
        """
        import os
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["QT_QUICK_BACKEND"] = "software"
        from pathlib import Path
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine
        from aicutting.gui.backend import Backend

        app = QGuiApplication([])
        qml = Path("src/aicutting/gui/qml")
        for status in ["idle", "compose", "working", "result", "error"]:
            backend = Backend()
            backend._status = status
            engine = QQmlApplicationEngine()
            engine.addImportPath(str(qml))
            engine.rootContext().setContextProperty("backend", backend)
            engine.load(str(qml / "Main.qml"))
            assert engine.rootObjects(), f"Main.qml failed to load in state {status}"
        print("QML_OK")
        """
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert "QML_OK" in result.stdout, result.stderr
