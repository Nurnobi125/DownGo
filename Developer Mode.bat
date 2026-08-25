@echo off
setlocal
title DownGo - Developer Mode

echo ============================================
echo   DownGo - Developer Mode Launcher
echo ============================================
echo.
echo This sets DOWNGO_DEV_MODE for THIS run only.
echo Your password is never written to disk.
echo.

set DOWNGO_DEV_MODE=1
set /p DOWNGO_DEV_PASSWORD=Enter your developer password (used to unlock Pro in-app): 

if "%DOWNGO_DEV_PASSWORD%"=="" (
    echo.
    echo No password entered - exiting.
    pause
    exit /b 1
)

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

if exist "%SCRIPT_DIR%dist\DownGo\DownGo.exe" (
    echo.
    echo Launching compiled build: dist\DownGo\DownGo.exe
    start "" "%SCRIPT_DIR%dist\DownGo\DownGo.exe"
) else (
    echo.
    echo No compiled build found - running from source instead.
    where python >nul 2>nul
    if errorlevel 1 (
        echo.
        echo ERROR: Python was not found on PATH, and no dist\DownGo\DownGo.exe exists.
        echo Either build the app first ^(build_exe.bat^) or install Python.
        pause
        exit /b 1
    )
    python "%SCRIPT_DIR%main.py"
)

endlocal