import hashlib
import mimetypes
import os
import re
import socket
import subprocess
import threading
import time
from urllib.parse import unquote, urlparse

import requests
from PySide6.QtCore import QObject, Signal


def get_file_type_info(filename):
    _, ext = os.path.splitext(filename.lower())
    
    types = {
        "Images": (("png", "jpg", "jpeg", "gif", "webp", "bmp", "svg", "ico"), "Images 🖼️"),
        "PDFs": (("pdf",), "PDFs 📄"),
        "Archives": (("zip", "rar", "7z", "tar", "gz", "bz2", "iso"), "Archives 📦"),
        "Video": (("mp4", "mkv", "avi", "mov", "wmv", "flv", "webm"), "Video 🎥"),
        "Audio": (("mp3", "wav", "flac", "aac", "ogg", "m4a"), "Audio 🎵")
    }
    
    clean_ext = ext.lstrip(".")
    for category, (ext_list, display) in types.items():
        if clean_ext in ext_list:
            return display, category
            
    return "Document 📁", "Documents"


def filename_from_headers(url, headers, fallback="download.bin"):
    cd = headers.get("Content-Disposition", "")
    name = ""
    if cd:
        m = re.search(r"filename\*\s*=\s*[^']*''([^;]+)", cd, re.I)
        if m:
            name = unquote(m.group(1).strip().strip('"'))
            name = os.path.basename(name)
        if not name:
            m = re.search(r'filename\s*=\s*"([^"]+)"', cd, re.I)
            if not m:
                m = re.search(r"filename\s*=\s*([^;]+)", cd, re.I)
            if m:
                name = m.group(1).strip().strip('"')
                name = os.path.basename(name)

    if not name:
        path = unquote(urlparse(url).path)
        name = os.path.basename(path)

    name = name or fallback

    _, ext = os.path.splitext(name)
    if not ext or ext.lower() == ".bin":
        ct = headers.get("Content-Type", "")
        if ct:
            ct_clean = ct.split(";")[0].strip().lower()
            guessed_ext = mimetypes.guess_extension(ct_clean)
            if guessed_ext:
                if not ext:
                    name += guessed_ext
                elif ext.lower() == ".bin" and guessed_ext != ".bin":
                    name = name[:-4] + guessed_ext

    return name


class FastDownloadOptimizer:
    @staticmethod
    def get_optimal_chunk_and_threads(file_size, user_threads):
        if file_size <= 0:
            return 1, 64 * 1024
        
        if file_size < 10 * 1024 * 1024:
            optimal_threads = min(user_threads, 4)
            chunk_size = 128 * 1024
        elif file_size < 100 * 1024 * 1024:
            optimal_threads = min(user_threads, 8)
            chunk_size = 256 * 1024
        else:
            optimal_threads = user_threads
            chunk_size = 512 * 1024
            
        return max(1, optimal_threads), chunk_size

    @staticmethod
    def configure_socket_buffers(sock_obj, receive_buffer_kb=512):
        try:
            buf_size = receive_buffer_kb * 1024
            sock_obj.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, buf_size)
            sock_obj.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except Exception:
            pass


class DownloadTask(QObject):
    changed = Signal()
    finished = Signal(object)
    failed = Signal(object, str)

    def __init__(self, task_id, url, folder, connections=4, proxy=None, filename_hint=None,
                 speed_limit_kbps=0, auth_user="", auth_pass="", enable_scan=True):
        super().__init__()
        self.id = task_id
        self.url = url
        self.base_folder = folder
        self.requested_connections = max(1, min(16, int(connections)))
        self.connections = self.requested_connections
        self.proxy = proxy
        self.speed_limit_bytes = speed_limit_kbps * 1024
        self.auth_user = auth_user
        self.auth_pass = auth_pass
        self.enable_scan = enable_scan

        self.filename = os.path.basename(filename_hint) if filename_hint else ""
        self.filename = self.filename or f"download-{task_id}.bin"

        _, subcat = get_file_type_info(self.filename)
        self.folder = os.path.join(self.base_folder, subcat)
        self.path = os.path.join(self.folder, self.filename)

        self.total = 0
        self.downloaded = 0
        self.speed = 0
        self.status = "Queued"
        self.eta = None
        self.error = ""
        self.sha256 = ""
        self.chunk_size = 128 * 1024

        self._stop = threading.Event()
        self._pause = threading.Event()
        self._threads = []
        self._lock = threading.Lock()
        self._last_bytes = 0
        self._last_time = time.time()
        self._ranges = []

    def _auth(self):
        if self.auth_user or self.auth_pass:
            return (self.auth_user, self.auth_pass)
        return None

    def _proxies(self):
        if not self.proxy:
            return None
        return {"http": self.proxy, "https": self.proxy}

    def start(self):
        if self.status in ("Downloading", "Checking...", "Merging", "Scanning..."):
            return
        self._stop.clear()
        self._pause.clear()
        threading.Thread(target=self._run, daemon=True).start()

    def pause(self):
        if self.status in ("Downloading", "Checking...", "Merging"):
            self._pause.set()
            self.status = "Paused"
            self.changed.emit()

    def resume(self):
        if self.status == "Paused":
            self._pause.clear()
            self.status = "Downloading"
            self.changed.emit()

    def cancel(self):
        self._stop.set()
        self.status = "Cancelled"
        self.changed.emit()

    def _throttle(self, chunk_len):
        if self.speed_limit_bytes > 0:
            expected_time = chunk_len / self.speed_limit_bytes
            time.sleep(expected_time)

    def _probe(self):
        headers = {"Range": "bytes=0-0"}
        r = requests.get(
            self.url, headers=headers, stream=True, timeout=20,
            allow_redirects=True, proxies=self._proxies(), auth=self._auth()
        )
        r.raise_for_status()

        cr = r.headers.get("Content-Range", "")
        if "/" in cr:
            try:
                total = int(cr.rsplit("/", 1)[1])
            except ValueError:
                total = int(r.headers.get("Content-Length", "0") or 0)
            ranged = r.status_code == 206
        else:
            total = int(r.headers.get("Content-Length", "0") or 0)
            ranged = False

        _, ext = os.path.splitext(self.filename)
        if self.filename.startswith("download-") or self.filename.endswith(".bin") or not ext:
            guessed = filename_from_headers(r.url, r.headers, self.filename)
            if guessed:
                self.filename = guessed
                _, subcat = get_file_type_info(self.filename)
                self.folder = os.path.join(self.base_folder, subcat)
                self.path = os.path.join(self.folder, self.filename)

        final_url = r.url
        r.close()
        return total, ranged, final_url

    def _compute_hash(self):
        hasher = hashlib.sha256()
        with open(self.path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                hasher.update(chunk)
        self.sha256 = hasher.hexdigest()

    def _run_defender_scan(self):
        if os.name != "nt" or not self.enable_scan:
            return
        defender_path = r"C:\Program Files\Windows Defender\MpCmdRun.exe"
        if os.path.exists(defender_path):
            self.status = "Scanning..."
            self.changed.emit()
            try:
                subprocess.run(
                    [defender_path, "-Scan", "-ScanType", "3", "-File", os.path.abspath(self.path)],
                    timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except Exception:
                pass

    def _run(self):
        try:
            os.makedirs(self.folder, exist_ok=True)
            self.status = "Checking..."
            self.changed.emit()

            total, ranged, _ = self._probe()
            self.total = total

            if total <= 0:
                raise RuntimeError("Server did not provide a usable file size.")

            self.connections, self.chunk_size = FastDownloadOptimizer.get_optimal_chunk_and_threads(
                self.total, self.requested_connections
            )

            if not ranged or self.connections == 1:
                self._single()
            else:
                self._multi()

            if self.downloaded >= self.total and not self._stop.is_set():
                self._compute_hash()
                self._run_defender_scan()
                self.status = "Completed"
                self.finished.emit(self)

        except Exception as e:
            if self.status != "Cancelled":
                self.status = "Error"
                self.error = str(e)
                self.failed.emit(self, str(e))
                self.changed.emit()

    def _single(self):
        existing = os.path.getsize(self.path) if os.path.exists(self.path) else 0
        if existing >= self.total:
            self.downloaded = self.total
            return

        self.downloaded = existing
        headers = {"Range": f"bytes={existing}-"} if existing else {}
        self.status = "Downloading"
        self.changed.emit()

        with requests.get(
            self.url, headers=headers, stream=True, timeout=30,
            proxies=self._proxies(), auth=self._auth()
        ) as r:
            r.raise_for_status()
            
            if existing > 0 and r.status_code != 206:
                existing = 0
                self.downloaded = 0
                mode = "wb"
            else:
                mode = "ab" if existing else "wb"

            with open(self.path, mode) as f:
                for chunk in r.iter_content(self.chunk_size):
                    if self._stop.is_set():
                        return
                    while self._pause.is_set() and not self._stop.is_set():
                        time.sleep(0.15)
                    if not chunk:
                        continue
                    self._throttle(len(chunk))
                    f.write(chunk)
                    with self._lock:
                        self.downloaded += len(chunk)
                    if self._metrics():
                        self.changed.emit()

    def _multi(self):
        part_dir = self.path + ".parts"
        os.makedirs(part_dir, exist_ok=True)

        self._ranges = []
        chunk = max(1, self.total // self.connections)
        for i in range(self.connections):
            start = i * chunk
            end = self.total - 1 if i == self.connections - 1 else min(self.total - 1, (i + 1) * chunk - 1)
            self._ranges.append((i, start, end))

        self.downloaded = 0
        for i, start, end in self._ranges:
            pp = os.path.join(part_dir, f"part_{i}.bin")
            max_allowed = end - start + 1
            if os.path.exists(pp):
                size = os.path.getsize(pp)
                if size > max_allowed:
                    with open(pp, "ab") as f:
                        f.truncate(max_allowed)
                    size = max_allowed
                self.downloaded += size

        self.status = "Downloading"
        self.changed.emit()

        self._threads = []
        for i, start, end in self._ranges:
            t = threading.Thread(
                target=self._part,
                args=(i, start, end, part_dir),
                daemon=True
            )
            self._threads.append(t)
            t.start()

        while any(t.is_alive() for t in self._threads):
            if self._stop.is_set():
                return
            if self._metrics():
                self.changed.emit()
            time.sleep(0.1)

        if self._stop.is_set():
            return

        if self.downloaded < self.total:
            raise RuntimeError(self.error or "Download did not complete.")

        self.status = "Merging"
        self.changed.emit()

        with open(self.path, "wb") as out:
            for i, _, _ in self._ranges:
                pp = os.path.join(part_dir, f"part_{i}.bin")
                with open(pp, "rb") as f:
                    while True:
                        buf = f.read(1024 * 1024)
                        if not buf:
                            break
                        out.write(buf)

        import shutil
        shutil.rmtree(part_dir, ignore_errors=True)

    def _part(self, i, start, end, part_dir):
        pp = os.path.join(part_dir, f"part_{i}.bin")
        have = os.path.getsize(pp) if os.path.exists(pp) else 0
        pos = start + have

        if pos > end:
            return

        headers = {"Range": f"bytes={pos}-{end}"}

        try:
            with requests.get(
                self.url, headers=headers, stream=True, timeout=30,
                proxies=self._proxies(), auth=self._auth()
            ) as r:
                r.raise_for_status()
                with open(pp, "ab") as f:
                    for data in r.iter_content(self.chunk_size):
                        if self._stop.is_set():
                            return
                        while self._pause.is_set() and not self._stop.is_set():
                            time.sleep(0.15)
                        if data:
                            self._throttle(len(data))
                            f.write(data)
                            with self._lock:
                                self.downloaded += len(data)
        except Exception as e:
            self.error = str(e)
            self._stop.set()

    def _metrics(self):
        now = time.time()
        dt = now - self._last_time
        if dt >= 0.5:
            with self._lock:
                delta = self.downloaded - self._last_bytes
                self.speed = max(0, delta / dt)
                self._last_bytes = self.downloaded
                self._last_time = now

                if self.speed > 0 and self.total:
                    self.eta = max(0, int((self.total - self.downloaded) / self.speed))
                else:
                    self.eta = None
            return True
        return False