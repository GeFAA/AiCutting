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
    echo Python was not found.
    echo Install Python 3.11 or newer, then start this file again.
    echo Download: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo Checking the existing Python environment...
py -3 -c "import aicutting; import PySide6, cv2, numpy, pydantic, typer, rich, librosa, scenedetect, soundfile" >nul 2>nul
if not errorlevel 1 (
    goto start_with_system_python
)

if exist ".venv\.aicutting-gui-ready" (
    goto start_with_venv
)

echo.
echo Dependencies are missing. AiCutting will create a local environment.
echo This happens only on the first setup and can take a few minutes.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Creating local Python environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo.
        echo The local Python environment could not be created.
        echo Check whether the drive containing this repository has enough free space.
        echo.
        pause
        exit /b 1
    )
)

echo Installing AiCutting Studio...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo.
    echo Pip could not be upgraded.
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -e ".[gui]"
if errorlevel 1 (
    echo.
    echo AiCutting Studio could not be installed.
    echo If you see "No space left on device", free disk space and try again.
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
    echo Warning: FFmpeg was not found on PATH.
    echo Rendering can fail until FFmpeg is installed.
    echo.
)
echo Starting AiCutting Studio...
echo.
py -3 -m aicutting.cli gui
goto handle_exit

:start_with_venv
where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo.
    echo Warning: FFmpeg was not found on PATH.
    echo Rendering can fail until FFmpeg is installed.
    echo.
)
echo Starting AiCutting Studio...
echo.
".venv\Scripts\python.exe" -m aicutting.cli gui

:handle_exit
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" (
    echo.
    echo AiCutting Studio exited with error code %EXITCODE%.
    echo.
    pause
    exit /b %EXITCODE%
)

exit /b 0
