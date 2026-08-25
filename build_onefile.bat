@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
python -m pip install pyinstaller
if not exist "icon.ico" (
    echo ERROR: icon.ico not found in this folder.
    pause
    exit /b 1
)
pyinstaller --noconfirm --clean --windowed --onefile --name "DownGo" --icon "icon.ico" main.py
echo.
echo BUILD COMPLETE:
echo dist\DownGo.exe
pause
