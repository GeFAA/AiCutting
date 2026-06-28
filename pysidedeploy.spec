# Packaging config for AiCutting Studio (the QML desktop app).
# Build a standalone Windows app with:   pyside6-deploy -c pysidedeploy.spec
# Produces a windowed app (no console) under ./dist. Run on Windows with the project's
# Python/PySide6 (6.8+). The render pipeline still calls the system ffmpeg.exe separately.

[app]
title = AiCutting Studio
project_dir = .
input_file = studio.py
project_file =
exec_directory = dist
icon =

[python]
python_path =
android_packages =

[qt]
# The QML entry; the whole gui/qml folder is bundled as data via the Nuitka arg below.
qml_files = src/aicutting/gui/qml/Main.qml
# Trim the heavy QML plugins we never load -- the documented #1 size lever.
excluded_qml_plugins = QtWebEngine,QtQuick3D,QtCharts,QtSensors,QtTest,QtWebSockets
modules = Core,Gui,Qml,Quick,Network
# Always keep platforms + imageformats (the classic blank-window / missing-image gotcha).
plugins = platforms,imageformats,iconengines

[nuitka]
macos.permissions =
mode = standalone
# Windowed (no console); drop translations; bundle the QML folder so Main.qml loads at runtime.
extra_args = --quiet --windows-console-mode=disable --noinclude-qt-translations --include-data-dir=src/aicutting/gui/qml=aicutting/gui/qml
