import os
import sys
import subprocess
import requests
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QMessageBox

CURRENT_VERSION = "3.2.0"
GITHUB_REPO_OWNER = "Nurnobi125"  # স্ক্রিনশট অনুযায়ী আপনার ইউজারনেম
GITHUB_REPO_NAME = "DownGo"     # আপনার রিপোজিটরি নাম

class UpdateCheckThread(QThread):
    update_available = Signal(str, str, str)  # latest_version, download_url, release_notes

    def run(self):
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("tag_name", "").lstrip("v")
                release_notes = data.get("body", "No release notes available.")
                
                download_url = ""
                for asset in data.get("assets", []):
                    if asset.get("name", "").endswith(".exe"):
                        download_url = asset.get("browser_download_url", "")
                        break

                if latest_version and latest_version != CURRENT_VERSION and download_url:
                    self.update_available.emit(latest_version, download_url, release_notes)
        except Exception:
            pass


class InstallerDownloadThread(QThread):
    progress = Signal(int)
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, download_url):
        super().__init__()
        self.download_url = download_url

    def run(self):
        try:
            temp_dir = os.environ.get("TEMP", os.path.expanduser("~"))
            installer_path = os.path.join(temp_dir, "DownGo-Update-Setup.exe")

            with requests.get(self.download_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total_size = int(r.headers.get("content-length", 0))
                downloaded = 0

                with open(installer_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=64 * 1024):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                pct = int((downloaded / total_size) * 100)
                                self.progress.emit(pct)

            self.finished.emit(installer_path)
        except Exception as e:
            self.failed.emit(str(e))


def launch_installer_and_exit(installer_path, app_instance):
    """DownGo বন্ধ করে ইনো সেটআপ ফাইল রান করে"""
    try:
        subprocess.Popen([installer_path, "/SILENT"])
    except Exception:
        subprocess.Popen([installer_path])
    
    app_instance.exit_app()