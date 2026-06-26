@echo off
setlocal EnableExtensions
title AiCutting Studio

cd /d "%~dp0"
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"

echo.
echo AiCutting Studio
echo =================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python wurde nicht gefunden.
    echo Bitte Python 3.11 oder neuer installieren und danach diese Datei erneut starten.
    echo Download: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo Pruefe vorhandenes Python...
py -3 -c "import aicutting; import PySide6, cv2, numpy, pydantic, typer, rich, librosa, scenedetect, soundfile" >nul 2>nul
if not errorlevel 1 (
    goto start_with_system_python
)

if exist ".venv\.aicutting-gui-ready" (
    goto start_with_venv
)

echo.
echo Abhaengigkeiten fehlen. AiCutting richtet jetzt eine lokale Umgebung ein.
echo Das passiert nur beim ersten Start und kann einige Minuten dauern.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Lokale Python-Umgebung wird erstellt...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo.
        echo Die lokale Python-Umgebung konnte nicht erstellt werden.
        echo Pruefe bitte, ob auf Laufwerk C: genug Speicher frei ist.
        echo.
        pause
        exit /b 1
    )
)

echo AiCutting Studio wird installiert...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo.
    echo Pip konnte nicht aktualisiert werden.
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -e ".[gui]"
if errorlevel 1 (
    echo.
    echo AiCutting Studio konnte nicht installiert werden.
    echo Falls "No space left on device" erscheint, bitte Speicher auf Laufwerk C: freimachen.
    echo.
    pause
    exit /b 1
)

echo ready > ".venv\.aicutting-gui-ready"
goto start_with_venv

:start_with_system_python
where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo.
    echo Hinweis: FFmpeg wurde nicht auf PATH gefunden.
    echo Rendern kann fehlschlagen, bis FFmpeg installiert ist.
    echo.
)
echo Starte AiCutting Studio...
echo.
py -3 -m aicutting.cli gui
goto handle_exit

:start_with_venv
where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo.
    echo Hinweis: FFmpeg wurde nicht auf PATH gefunden.
    echo Rendern kann fehlschlagen, bis FFmpeg installiert ist.
    echo.
)
echo Starte AiCutting Studio...
echo.
".venv\Scripts\python.exe" -m aicutting.cli gui

:handle_exit
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" (
    echo.
    echo AiCutting Studio wurde mit Fehlercode %EXITCODE% beendet.
    echo.
    pause
    exit /b %EXITCODE%
)

exit /b 0
