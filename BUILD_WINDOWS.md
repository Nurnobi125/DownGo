# DownGo 4.0 Windows release

## 1. Build the desktop EXE
Open **Developer PowerShell / CMD on Windows 10/11**:

    py -3 -m venv .venv
    .venv\Scripts\activate
    python -m pip install -U pip
    pip install -r requirements.txt
    pip install pyinstaller
    build_exe.bat

Output: `dist\DownGo\DownGo.exe`

## 2. Build the installer
Install Inno Setup 6, then run `build_installer.bat`.

## 3. Build the MSIX package
After the EXE build:

    powershell -ExecutionPolicy Bypass -File msix\build_msix.ps1

For Microsoft Store, submit the MSIX/Store package through Partner Center. The Store handles signing/distribution; do not ship a self-signed package as the Store submission artifact.

## 4. Gumroad
Set `DOWNGO_GUMROAD_PRODUCT_ID` to the actual Gumroad product ID before building. Do not put a private API secret in the desktop application.

## 5. Browser integration
Load `browser_extension` as an unpacked MV3 extension during QA. Publish it separately to the Chrome/Edge extension stores if desired.


Microsoft Store identity configured for Partner Center:
Package Identity Name: MD.RAFIQULISLAM.BOKKAR.DownGo-FastDownloadManager
Publisher: CN=03A24960-07BF-4092-AD1A-2AD49909AF53
PublisherDisplayName: MD.RAFIQUL ISLAM .(BOKKAR)
Package Family Name: MD.RAFIQULISLAM.BOKKAR.DownGo-FastDownloadManager_q3rwgaaag29cw
Store ID: 9PP082NPWR27
