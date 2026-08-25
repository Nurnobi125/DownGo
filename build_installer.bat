@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo        DownGo 3.2 INSTALLER BUILD
echo ==========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python was not found.
    pause
    exit /b 1
)

echo [1/3] Installing Python dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
)

echo.
echo [2/3] Building DownGo application...
python -m pip install pyinstaller
if errorlevel 1 (
    echo ERROR: PyInstaller installation failed.
    pause
    exit /b 1
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

pyinstaller --noconfirm --clean --windowed --onedir --name "DownGo" --icon "icon.ico" main.py
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo [3/3] Building Windows installer...

set ISCC=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if "%ISCC%"=="" (
    echo.
    echo Inno Setup 6 was not found.
    echo Install Inno Setup 6, then run this file again.
    echo.
    echo Installer script: DownGo-Setup.iss
    pause
    exit /b 2
)

if exist installer rmdir /s /q installer
mkdir installer

"%ISCC%" "DownGo-Setup.iss"
if errorlevel 1 (
    echo ERROR: Inno Setup compilation failed.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo BUILD COMPLETE
echo ==========================================
echo Installer:
echo %CD%\installer\DownGo-Setup-v3.2.0.exe
echo.
pause
