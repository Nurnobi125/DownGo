from pathlib import Path
import ast
ROOT = Path(__file__).resolve().parent
files = ["main.py","app.py","downloader.py","speedtest.py","updater.py","bridge.py"]
for f in files:
    ast.parse((ROOT/f).read_text(encoding="utf-8"), filename=f)
assert "4.0.7" in (ROOT/"updater.py").read_text(encoding="utf-8")
manifest=(ROOT/"msix"/"AppxManifest.xml").read_text(encoding="utf-8")
assert 'Version="4.0.7.0"' in manifest
assert 'Name="MD.RAFIQULISLAM.BOKKAR.DownGo-FastDownloadManager"' in manifest
assert 'Publisher="CN=03A24960-07BF-4092-AD1A-2AD49909AF53"' in manifest
main=(ROOT/"main.py").read_text(encoding="utf-8")
assert 'background = "--background" in sys.argv' in main
assert 'window.hide()' in main
bat=(ROOT/"build_installer.bat").read_text(encoding="utf-8")
assert 'import PySide6, requests, yt_dlp' in bat
assert 'already installed - no reinstall required' in bat
assert 'gumroad' not in bat.lower()
assert 'license_manager' not in bat
app=(ROOT/"app.py").read_text(encoding="utf-8").lower()
assert 'gumroad' not in app and 'license_manager' not in app and 'unlock pro' not in app
print("DownGo 4.0.7 FREE STATIC QA: PASS")
