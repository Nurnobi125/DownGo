@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title DownGo 4.0.7 Build

echo ==========================================
echo       DownGo 4.0.7 BUILD / QA
 echo ==========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Python 3.11+ was not found.
    pause
    exit /b 1
)

set "PY=python"

echo [1/4] Verifying Python dependencies...
%PY% -c "import PySide6, requests, yt_dlp; print('[PASS] PySide6 / requests / yt-dlp imports OK')"
if errorlevel 1 (
    echo [INFO] Some dependencies are missing. Installing requirements...
    %PY% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [FAIL] Dependency installation failed.
        pause
        exit /b 1
    )
    %PY% -c "import PySide6, requests, yt_dlp; print('[PASS] Dependencies installed and verified')"
    if errorlevel 1 (
        echo [FAIL] Dependency import verification failed.
        pause
        exit /b 1
    )
) else (
    echo [PASS] Dependencies already installed - no reinstall required.
)

echo.
echo [2/4] Running release static QA...
%PY% -m py_compile main.py app.py downloader.py speedtest.py updater.py bridge.py
if errorlevel 1 (
    echo [FAIL] Python compile check failed.
    pause
    exit /b 1
)
%PY% QA_4_0_7_STATIC.py
if errorlevel 1 (
    echo [FAIL] Release static QA failed.
    pause
    exit /b 1
)
echo [PASS] Release static QA.

echo.
echo [3/4] Building DownGo application...
%PY% -m pip install pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [FAIL] PyInstaller is unavailable and could not be installed.
    pause
    exit /b 1
)
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
pyinstaller --noconfirm --clean --windowed --onedir --name "DownGo" --icon "icon.ico" --version-file "version_info.txt" --collect-all yt_dlp --add-data "config;config" main.py
if errorlevel 1 (
    echo [FAIL] PyInstaller build failed.
    pause
    exit /b 1
)
if not exist "dist\DownGo\DownGo.exe" (
    echo [FAIL] DownGo.exe was not produced.
    pause
    exit /b 1
)
echo [PASS] Application build.

echo.
echo [4/4] Building Windows installer...
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if "%ISCC%"=="" (
    echo [WARN] Inno Setup 6 not found. EXE build succeeded.
    echo Install Inno Setup 6 and run build_installer.bat again to create the installer.
    exit /b 2
)
if exist installer rmdir /s /q installer
mkdir installer
"%ISCC%" "DownGo-Setup.iss"
if errorlevel 1 (
    echo [FAIL] Inno Setup compilation failed.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo BUILD COMPLETE - DownGo 4.0.7
echo ==========================================
echo EXE:       %CD%\dist\DownGo\DownGo.exe
echo Installer: %CD%\installer\DownGo-Setup-v4.0.7.exe
echo.
pause
exit /b 0
