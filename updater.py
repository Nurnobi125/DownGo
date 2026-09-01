import os
import subprocess
import tempfile
import requests
from PySide6.QtCore import QThread, Signal

CURRENT_VERSION = "4.0.7"
GITHUB_REPO_OWNER = "Nurnobi125"
GITHUB_REPO_NAME = "DownGo"

class UpdateCheckThread(QThread):
    update_available = Signal(str, str, str)
    def run(self):
        try:
            r = requests.get(f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest",
                             timeout=10, headers={"Accept":"application/vnd.github+json", "User-Agent":"DownGo/4.0.7"})
            if r.status_code != 200: return
            data=r.json(); latest=data.get("tag_name","").lstrip("v")
            if not latest or latest == CURRENT_VERSION: return
            asset=next((a for a in data.get("assets",[]) if a.get("name","").lower().endswith((".exe",".msix"))),None)
            if asset and asset.get("browser_download_url"):
                self.update_available.emit(latest, asset["browser_download_url"], data.get("body","") or "No release notes available.")
        except Exception:
            pass

class InstallerDownloadThread(QThread):
    progress=Signal(int); finished=Signal(str); failed=Signal(str)
    def __init__(self, download_url): super().__init__(); self.download_url=download_url
    def run(self):
        try:
            fd,path=tempfile.mkstemp(prefix="DownGo-update-", suffix=".exe"); os.close(fd)
            with requests.get(self.download_url,stream=True,timeout=(10,60),headers={"User-Agent":"DownGo/4.0.7"}) as r:
                r.raise_for_status(); total=int(r.headers.get("content-length",0) or 0); done=0
                with open(path,"wb") as f:
                    for chunk in r.iter_content(256*1024):
                        if chunk: f.write(chunk); done+=len(chunk); self.progress.emit(int(done*100/total) if total else 0)
            self.finished.emit(path)
        except Exception as e: self.failed.emit(str(e))

def launch_installer_and_exit(installer_path, app_instance):
    subprocess.Popen([installer_path, "/SILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"])
    app_instance.exit_app()
