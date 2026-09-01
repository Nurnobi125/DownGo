@echo off
setlocal
cd /d "%~dp0"
title DownGo 4.0.6 Build
python -m pip install -U pip
python -m pip install -r requirements.txt
if not exist "config\gumroad_product_id.txt" (
  echo ERROR: Missing config\gumroad_product_id.txt
  echo Run set_gumroad_product_id.bat first.
  exit /b 1
)
findstr /C:"REPLACE_WITH_GUMROAD_PRODUCT_ID" config\gumroad_product_id.txt >nul
if not errorlevel 1 (
  echo ERROR: Gumroad Product ID is still a placeholder.
  echo Run set_gumroad_product_id.bat first.
  exit /b 1
)
python -m pip install -U pyinstaller
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
pyinstaller --noconfirm --clean --windowed --onedir --name "DownGo" --icon "icon.ico" --version-file "version_info.txt" --collect-all yt_dlp --add-data "config;config" main.py
if errorlevel 1 exit /b 1
copy /Y "config\gumroad_product_id.txt" "dist\DownGo\gumroad_product_id.txt" >nul
echo Build complete: dist\DownGo\DownGo.exe
