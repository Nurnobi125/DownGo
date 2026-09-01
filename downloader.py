"""DownGo 4.0 download engine.

Features:
- HTTP/HTTPS validation and redirects
- Robust HEAD/Range probing with browser-like headers
- Up to 16 parallel byte-range connections
- Safe resume using per-part files
- Automatic fallback to a single connection when Range is unsupported
- Retries with exponential backoff
- Aggregate speed limiting
- Optional yt-dlp media-page resolution (no DRM bypass)
- SHA-256 verification and optional Microsoft Defender scan
"""
from __future__ import annotations

import hashlib
import mimetypes
import os
import re
import shutil
import socket
import subprocess
import threading
import time
from urllib.parse import unquote, urlparse
from email.utils import parsedate_to_datetime

import requests
from requests.adapters import HTTPAdapter
from PySide6.QtCore import QObject, Signal

MAX_CONNECTIONS = 16
DEFAULT_TIMEOUT = (10, 60)
MAX_RETRIES = 6
RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36 DownGo/4.0.7"
)


def validate_url(url: str) -> str:
    url = (url or "").strip()
    p = urlparse(url)
    if p.scheme.lower() not in {"http", "https"} or not p.netloc:
        raise ValueError("Please enter a valid HTTP/HTTPS URL.")
    return url


def safe_filename(name: str, fallback="download.bin") -> str:
    name = unquote(str(name or "")).replace("\\", "/")
    name = os.path.basename(name).strip().strip(".")
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    if name in {"", ".", ".."}:
        name = fallback
    # Windows reserved names
    stem, ext = os.path.splitext(name)
    if stem.upper() in {"CON", "PRN", "AUX", "NUL"} or re.match(r"^(COM|LPT)[0-9]$", stem, re.I):
        name = "_" + name
    return name[:240]


def get_file_type_info(filename):
    _, ext = os.path.splitext((filename or "").lower())
    types = {
        "Images": (("png", "jpg", "jpeg", "gif", "webp", "bmp", "svg", "ico", "avif"), "Images 🖼️"),
        "PDFs": (("pdf",), "PDFs 📄"),
        "Archives": (("zip", "rar", "7z", "tar", "gz", "bz2", "iso", "xz"), "Archives 📦"),
        "Video": (("mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v"), "Video 🎥"),
        "Audio": (("mp3", "wav", "flac", "aac", "ogg", "m4a", "opus", "wma"), "Audio 🎵"),
        "Programs": (("exe", "msi", "msix", "appx", "dmg", "deb", "rpm"), "Programs 💻"),
        "Documents": (("doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "csv", "rtf"), "Documents 📁"),
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
        if not name:
            m = re.search(r'filename\s*=\s*"([^"]+)"', cd, re.I) or re.search(r"filename\s*=\s*([^;]+)", cd, re.I)
            if m:
                name = m.group(1).strip().strip('"')
    if not name:
        name = os.path.basename(unquote(urlparse(url).path))
    name = safe_filename(name, fallback)
    _, ext = os.path.splitext(name)
    if not ext or ext.lower() == ".bin":
        ct = headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        guessed = mimetypes.guess_extension(ct) if ct else None
        if guessed and guessed != ".bin":
            name = os.path.splitext(name)[0] + guessed
    return name


def human_error(exc) -> str:
    text = str(exc).strip()
    if isinstance(exc, requests.exceptions.Timeout):
        return "Connection timed out. Check your internet connection and try again."
    if isinstance(exc, requests.exceptions.ConnectionError):
        return "Could not connect to the server. Check your internet connection or try again."
    if "403" in text:
        return "Server denied the request (HTTP 403). The link may require an active browser session or permission."
    if "404" in text:
        return "File not found (HTTP 404). The URL may have expired or been removed."
    if "429" in text:
        return "Too many requests (HTTP 429). Please wait and retry."
    if "415" in text:
        return "The server rejected this file type (HTTP 415)."
    if "416" in text:
        return "The requested resume range is no longer valid. DownGo will safely retry from the beginning."
    if "500" in text or "502" in text or "503" in text or "504" in text:
        return "The server is temporarily unavailable. Please retry the download."
    return text or "Download failed."


def check_resume_capability(url: str) -> bool:
    """Lightweight, UI-safe resume capability check. Never raises to callers."""
    try:
        url = validate_url(url)
        headers = {"User-Agent": USER_AGENT, "Accept": "*/*", "Accept-Encoding": "identity", "Range": "bytes=0-0"}
        with requests.get(url, headers=headers, timeout=(5, 15), allow_redirects=True, stream=True) as r:
            return r.status_code == 206 and bool(r.headers.get("Content-Range"))
    except requests.RequestException:
        return False


class FastDownloadOptimizer:
    @staticmethod
    def get_optimal_chunk_and_threads(file_size, user_threads):
        threads = max(1, min(MAX_CONNECTIONS, int(user_threads or 1)))
        if file_size <= 0:
            return 1, 256 * 1024
        if file_size < 10 * 1024 * 1024:
            return min(threads, 4), 128 * 1024
        if file_size < 100 * 1024 * 1024:
            return min(threads, 8), 256 * 1024
        return threads, 512 * 1024

    @staticmethod
    def configure_socket_buffers(sock_obj, receive_buffer_kb=512):
        try:
            sock_obj.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, receive_buffer_kb * 1024)
            sock_obj.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except Exception:
            pass


class _RateLimiter:
    def __init__(self, bytes_per_sec=0):
        self.rate = max(0, int(bytes_per_sec or 0))
        self.lock = threading.Lock()
        self.started = time.monotonic()
        self.sent = 0

    def wait(self, amount):
        if self.rate <= 0 or amount <= 0:
            return
        with self.lock:
            self.sent += amount
            target = self.sent / self.rate
            elapsed = time.monotonic() - self.started
            delay = target - elapsed
        if delay > 0:
            time.sleep(min(delay, 2.0))


class DownloadTask(QObject):
    changed = Signal()
    finished = Signal(object)
    failed = Signal(object, str)

    def __init__(self, task_id, url, folder, connections=4, proxy=None, filename_hint=None,
                 speed_limit_kbps=0, auth_user="", auth_pass="", enable_scan=True, referrer="", lite_mode=False):
        super().__init__()
        self.id = task_id
        self.url = validate_url(url)
        self.base_folder = os.path.abspath(os.path.expanduser(folder))
        self.requested_connections = max(1, min(MAX_CONNECTIONS, int(connections or 1)))
        self.connections = self.requested_connections
        self.acceleration_mode = "Multi-range" if self.connections > 1 else "Single connection"
        self.proxy = proxy
        self.speed_limit_bytes = max(0, int(speed_limit_kbps or 0)) * 1024
        self.auth_user = auth_user
        self.auth_pass = auth_pass
        self.enable_scan = bool(enable_scan)
        self.referrer = referrer or ""
        self.lite_mode = bool(lite_mode)

        self.filename = safe_filename(filename_hint, f"download-{task_id}.bin") if filename_hint else f"download-{task_id}.bin"
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
        self.chunk_size = 256 * 1024
        self.can_resume = None
        self.scan_status = "not_requested"
        self.scan_message = ""
        self.final_url = self.url

        self._stop = threading.Event()
        self._pause = threading.Event()
        self._threads = []
        self._lock = threading.Lock()
        self._worker_failed = threading.Event()
        self._worker_error = ""
        self._last_bytes = 0
        self._last_time = time.monotonic()
        self._ranges = []
        self._limiter = _RateLimiter(self.speed_limit_bytes)
        self._session_headers = {"User-Agent": USER_AGENT, "Accept": "*/*", "Accept-Encoding": "identity"}
        if self.referrer:
            self._session_headers["Referer"] = self.referrer

    def _auth(self):
        return (self.auth_user, self.auth_pass) if (self.auth_user or self.auth_pass) else None

    def _proxies(self):
        return {"http": self.proxy, "https": self.proxy} if self.proxy else None

    def _new_session(self):
        session = requests.Session()
        pool = 2 if self.lite_mode else 4
        adapter = HTTPAdapter(pool_connections=pool, pool_maxsize=max(pool, self.requested_connections + 2), max_retries=0)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update(self._session_headers)
        return session

    def _request_once(self, session, method="GET", **kwargs):
        headers = dict(self._session_headers)
        headers.update(kwargs.pop("headers", {}) or {})
        return session.request(
            method, self.final_url or self.url, headers=headers, timeout=DEFAULT_TIMEOUT,
            allow_redirects=True, proxies=self._proxies(), auth=self._auth(), **kwargs
        )

    @staticmethod
    def _retry_delay(response, attempt):
        value = response.headers.get("Retry-After", "") if response is not None else ""
        try:
            delay = float(value)
        except (TypeError, ValueError):
            try:
                if value:
                    delay = max(0.0, (parsedate_to_datetime(value).timestamp() - time.time()))
                else:
                    raise ValueError
            except Exception:
                delay = min(8.0, 0.6 * (2 ** attempt))
        return max(0.25, min(delay, 30.0))

    def _request_retry(self, method="GET", **kwargs):
        session = kwargs.pop("_session", None) or self._new_session()
        owns_session = kwargs.pop("_owns_session", True)
        last_exc = None
        try:
            for attempt in range(MAX_RETRIES):
                if self._stop.is_set():
                    raise RuntimeError("Download cancelled.")
                try:
                    response = self._request_once(session, method, **kwargs)
                    if response.status_code in RETRYABLE_STATUS_CODES:
                        if attempt + 1 < MAX_RETRIES:
                            response.close()
                            time.sleep(self._retry_delay(response, attempt))
                            continue
                    self.final_url = response.url or self.final_url
                    return response
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                    last_exc = exc
                    if attempt + 1 >= MAX_RETRIES:
                        raise
                    time.sleep(min(8.0, 0.6 * (2 ** attempt)))
                except requests.exceptions.RequestException as exc:
                    last_exc = exc
                    if attempt + 1 >= MAX_RETRIES:
                        raise
                    time.sleep(min(8.0, 0.6 * (2 ** attempt)))
            if last_exc:
                raise last_exc
            raise RuntimeError("Request failed.")
        finally:
            if owns_session:
                session.close()

    def _request(self, method="GET", **kwargs):
        return self._request_retry(method, **kwargs)

    def start(self):
        if self.status in {"Downloading", "Checking...", "Merging", "Scanning..."}:
            return
        self._stop.clear()
        self._pause.clear()
        threading.Thread(target=self._run, name=f"DownGo-{self.id}", daemon=True).start()

    def pause(self):
        if self.status in {"Downloading", "Checking...", "Merging"}:
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
        self._pause.clear()
        self.status = "Cancelled"
        self.changed.emit()

    def _probe_direct(self):
        """Probe a URL without assuming HEAD is reliable.

        A one-byte GET is authoritative because many file hosts omit/lie about
        Accept-Ranges on HEAD, and some CDNs block HEAD entirely. The response
        body is sniffed just enough to distinguish a real file (including PDF)
        from an HTML error/viewer page.
        """
        head_headers = {}
        head_url = self.final_url or self.url

        # HEAD is metadata-only and optional. Never let a broken HEAD endpoint
        # prevent a valid GET download.
        try:
            with self._request_retry("HEAD") as head:
                if head.status_code < 400:
                    head_headers = dict(head.headers)
                    head_url = head.url or head_url
        except requests.RequestException:
            pass

        try:
            head_total = int(head_headers.get("Content-Length", "0") or 0)
        except (TypeError, ValueError):
            head_total = 0

        r = self._request_retry("GET", headers={"Range": "bytes=0-0"}, stream=True)
        try:
            if r.status_code >= 400:
                r.raise_for_status()

            content_type = (r.headers.get("Content-Type") or head_headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
            cr = r.headers.get("Content-Range", "")
            total = 0
            range_supported = False
            if r.status_code == 206 and cr:
                m = re.match(r"^bytes\s+(\d+)-(\d+)/(\d+|\*)$", cr.strip(), re.I)
                if not m or int(m.group(1)) != 0 or int(m.group(2)) != 0:
                    raise RuntimeError("Server returned an invalid byte-range response.")
                range_supported = True
                if m.group(3) != "*":
                    total = int(m.group(3))

            if not total:
                try:
                    total = int(r.headers.get("Content-Length", "0") or 0)
                except (TypeError, ValueError):
                    total = 0
            if not total:
                total = head_total

            # Read only the tiny probe body. This also lets us identify PDF and
            # HTML when servers use generic application/octet-stream.
            try:
                first = next(r.iter_content(4096), b"") or b""
            except Exception:
                first = b""

            looks_pdf = first.startswith(b"%PDF-")
            looks_html = first.lstrip().lower().startswith((b"<!doctype html", b"<html", b"<head", b"<body", b"<?xml"))
            if "text/html" in content_type and not looks_pdf:
                raise _WebpageURL()
            if looks_html and not looks_pdf:
                raise _WebpageURL()

            final_url = r.url or head_url
            # Some servers expose Content-Disposition only on HEAD while their
            # ranged GET omits it. Merge both response header sets so a PDF (or
            # any file) keeps the server-provided filename during the actual
            # download. GET headers remain authoritative when both are present.
            merged_headers = dict(head_headers)
            merged_headers.update(r.headers)
            name = filename_from_headers(final_url, merged_headers, self.filename)
            # Prefer the authoritative response headers. If the host gives a
            # generic filename, infer a useful extension from MIME/signature.
            if looks_pdf and (name.lower().endswith(".bin") or not os.path.splitext(name)[1]):
                name = os.path.splitext(name)[0] + ".pdf"
            if name and (self.filename.startswith("download-") or self.filename.endswith(".bin")):
                self._set_filename(name)
            self.final_url = final_url
            return total, range_supported, final_url, content_type
        finally:
            try:
                r.close()
            except Exception:
                pass

    def _resolve_webpage(self):
        """Resolve supported media pages with yt-dlp when available.

        This does not bypass DRM, paywalls, private content, or access controls.
        """
        try:
            import yt_dlp
        except ImportError:
            raise RuntimeError("This URL is a webpage, not a direct file URL. Install the optional yt-dlp package to enable supported media-page downloads.")
        opts = {"quiet": True, "no_warnings": True, "noplaylist": True, "skip_download": True}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
            if not info:
                raise RuntimeError("Could not resolve this webpage to a downloadable media file.")
            if info.get("is_live"):
                raise RuntimeError("Live streams are not supported by DownGo's resumable file engine.")
            chosen = info
            if info.get("requested_formats"):
                # Prefer a progressive format; otherwise use the first video/audio URL.
                chosen = next((x for x in info["requested_formats"] if x.get("url")), info)
            media_url = chosen.get("url") or info.get("url")
            if not media_url:
                raise RuntimeError("The webpage did not expose a downloadable media URL.")
            self.final_url = media_url
            title = info.get("title") or self.filename
            ext = info.get("ext") or "bin"
            self._set_filename(safe_filename(f"{title}.{ext}"))
            return self._probe_direct()
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"Media URL resolution failed: {e}") from e

    def _set_filename(self, name):
        self.filename = safe_filename(name, self.filename)
        _, subcat = get_file_type_info(self.filename)
        self.folder = os.path.join(self.base_folder, subcat)
        self.path = os.path.join(self.folder, self.filename)

    def _probe(self):
        self.final_url = self.url
        try:
            return self._probe_direct()
        except _WebpageURL:
            return self._resolve_webpage()

    def _compute_hash(self):
        hasher = hashlib.sha256()
        with open(self.path, "rb") as f:
            while True:
                buf = f.read(1024 * 1024)
                if not buf: break
                hasher.update(buf)
        self.sha256 = hasher.hexdigest()

    def _run_defender_scan(self):
        """Run one bounded Microsoft Defender scan before completion/extraction.
        Return True only when Defender explicitly reports a clean scan (0).
        Code 2 is treated as a security warning, never as clean.
        """
        if not self.enable_scan:
            self.scan_status = "not_requested"
            return True
        if os.name != "nt":
            self.scan_status = "unavailable"
            self.scan_message = "Windows Defender is only available on Windows."
            return True
        candidates = [
            os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Windows Defender", "MpCmdRun.exe"),
            os.path.join(os.environ.get("ProgramW6432", r"C:\Program Files"), "Windows Defender", "MpCmdRun.exe"),
            os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Windows Defender", "Platform", "MpCmdRun.exe"),
        ]
        defender = next((x for x in candidates if os.path.isfile(x)), None)
        if not defender:
            self.scan_status = "unavailable"
            self.scan_message = "Microsoft Defender command-line scanner was not found."
            return True
        self.scan_status = "scanning"
        self.status = "Scanning..."
        self.changed.emit()
        try:
            result = subprocess.run([defender, "-Scan", "-ScanType", "3", "-File", os.path.abspath(self.path)],
                                    timeout=180, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if result.returncode == 0:
                self.scan_status = "clean"
                self.scan_message = "Microsoft Defender scan completed clean."
                return True
            self.scan_status = "threat" if result.returncode == 2 else "error"
            self.scan_message = "Microsoft Defender reported a threat or could not confirm the file as clean."
            self.error = self.scan_message
            return False
        except subprocess.TimeoutExpired:
            self.scan_status = "error"
            self.scan_message = "Microsoft Defender scan timed out."
            self.error = self.scan_message
            return False
        except Exception as exc:
            self.scan_status = "error"
            self.scan_message = f"Antivirus scan failed: {exc}"
            self.error = self.scan_message
            return False

    def _run(self):
        try:
            os.makedirs(self.folder, exist_ok=True)
            self.status = "Checking..."
            self.error = ""
            self.changed.emit()
            total, ranged, final_url, _ = self._probe()
            self.final_url = final_url or self.final_url
            # Filename/category may change after HTTP headers are inspected
            # (e.g. a URL with no .pdf extension). Re-create the destination
            # directory after probing so single-connection downloads never fail
            # with a missing PDFs/Music/Video directory.
            os.makedirs(self.folder, exist_ok=True)
            self.total = max(0, total)
            if self.total <= 0:
                # A zero-size/unknown direct HTTP body is still possible. Use single mode.
                self.connections, self.chunk_size = 1, 256 * 1024
                self.acceleration_mode = "Single connection"
                self._single(unknown_size=True)
            else:
                if self.lite_mode:
                    self.connections = min(2, self.requested_connections)
                    self.chunk_size = 128 * 1024
                    self.acceleration_mode = "Lite multi-range" if self.connections > 1 and ranged else "Lite single connection"
                else:
                    self.connections, self.chunk_size = FastDownloadOptimizer.get_optimal_chunk_and_threads(self.total, self.requested_connections)
                    self.acceleration_mode = "Multi-range" if self.connections > 1 and ranged else "Single connection fallback"
                self.can_resume = bool(ranged)
                if not ranged or self.connections == 1:
                    self._single()
                else:
                    self._multi()

            if self._stop.is_set() or self.status == "Cancelled":
                return
            if self.total and self.downloaded < self.total:
                raise RuntimeError(self.error or "Download did not complete.")
            self._compute_hash()
            if not self._run_defender_scan():
                raise RuntimeError(self.error or "Security scan did not confirm this file as clean.")
            if self._stop.is_set(): return
            self.status = "Completed"
            self.finished.emit(self)
            self.changed.emit()
        except Exception as e:
            if self.status == "Cancelled" or self._stop.is_set():
                return
            self.status = "Error"
            self.error = human_error(e)
            self.failed.emit(self, self.error)
            self.changed.emit()

    def _wait_if_paused(self):
        while self._pause.is_set() and not self._stop.is_set():
            time.sleep(0.15)

    def _write_chunk(self, f, data):
        if not data: return
        self._wait_if_paused()
        if self._stop.is_set(): return
        self._limiter.wait(len(data))
        f.write(data)
        with self._lock:
            self.downloaded += len(data)

    def _single(self, unknown_size=False):
        self.status = "Downloading"
        self.changed.emit()
        restarted_without_range = False
        attempts = 0
        while not self._stop.is_set():
            existing = os.path.getsize(self.path) if os.path.exists(self.path) else 0
            if self.total and existing >= self.total:
                self.downloaded = self.total
                return
            start = existing
            headers = {"Range": f"bytes={start}-"} if start else {}
            try:
                with self._request_retry("GET", headers=headers, stream=True) as r:
                    if r.status_code >= 400:
                        r.raise_for_status()
                    if start:
                        if r.status_code == 416:
                            if self.total and existing == self.total:
                                self.downloaded = self.total
                                return
                            if restarted_without_range:
                                raise RuntimeError("The server rejected resume and the partial file could not be restarted safely.")
                            with open(self.path, "wb"): pass
                            self.downloaded = 0
                            restarted_without_range = True
                            continue
                        if r.status_code != 206:
                            if restarted_without_range:
                                raise RuntimeError("Server does not support resume for this file.")
                            with open(self.path, "wb"): pass
                            self.downloaded = 0
                            restarted_without_range = True
                            continue
                        cr = r.headers.get("Content-Range", "")
                        m = re.match(r"^bytes\s+(\d+)-(\d+)/(\d+|\*)$", cr.strip(), re.I)
                        if not m or int(m.group(1)) != start:
                            raise RuntimeError("Server returned an invalid resume range.")
                        if m.group(3) != "*" and self.total and int(m.group(3)) != self.total:
                            raise RuntimeError("Server changed file size while resuming the download.")
                    else:
                        if r.status_code == 206:
                            cr = r.headers.get("Content-Range", "")
                            m = re.match(r"^bytes\s+(\d+)-(\d+)/(\d+|\*)$", cr.strip(), re.I)
                            if m and m.group(3) != "*" and not self.total:
                                self.total = int(m.group(3))
                    if not self.total:
                        try:
                            length = int(r.headers.get("Content-Length", "0") or 0)
                            self.total = length + start if length else 0
                        except (TypeError, ValueError):
                            self.total = 0
                    mode = "ab" if start else "wb"
                    with open(self.path, mode) as f:
                        for chunk in r.iter_content(chunk_size=self.chunk_size):
                            if self._stop.is_set(): return
                            self._write_chunk(f, chunk)
                            if self._metrics(): self.changed.emit()
                attempts = 0
                if not self.total or os.path.getsize(self.path) >= self.total:
                    return
                if os.path.getsize(self.path) <= existing:
                    raise RuntimeError("The server ended the download before any new data arrived.")
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError, requests.exceptions.RequestException) as exc:
                attempts += 1
                if attempts >= MAX_RETRIES:
                    raise RuntimeError(human_error(exc)) from exc
                time.sleep(min(8.0, 0.6 * (2 ** (attempts - 1))))
            except Exception:
                raise

    def _multi(self):
        part_dir = self.path + ".parts"
        os.makedirs(part_dir, exist_ok=True)
        self._ranges = []
        self._worker_failed.clear()
        self._worker_error = ""
        base = self.total // self.connections
        remainder = self.total % self.connections
        cursor = 0
        for i in range(self.connections):
            length = base + (1 if i < remainder else 0)
            end = cursor + length - 1
            self._ranges.append((i, cursor, end))
            cursor = end + 1

        self.downloaded = 0
        for i, start, end in self._ranges:
            pp = os.path.join(part_dir, f"part_{i}.bin")
            max_allowed = end - start + 1
            if os.path.exists(pp):
                size = min(os.path.getsize(pp), max_allowed)
                if os.path.getsize(pp) != size:
                    with open(pp, "r+b") as f: f.truncate(size)
                self.downloaded += size

        self.status = "Downloading"
        self.changed.emit()
        self._threads = [threading.Thread(target=self._part, args=(i, s, e, part_dir), daemon=True, name=f"DownGo-part-{i}")
                         for i, s, e in self._ranges]
        for t in self._threads: t.start()
        while any(t.is_alive() for t in self._threads):
            if self._stop.is_set(): return
            if self._metrics(): self.changed.emit()
            time.sleep(0.1)
        if self._stop.is_set(): return
        if self._worker_failed.is_set():
            raise RuntimeError(self._worker_error or "One or more download connections failed.")
        if self.downloaded < self.total:
            raise RuntimeError("Download did not complete.")

        self.status = "Merging"
        self.changed.emit()
        temp = self.path + ".downloading"
        with open(temp, "wb") as out:
            for i, start, end in self._ranges:
                pp = os.path.join(part_dir, f"part_{i}.bin")
                expected = end - start + 1
                if not os.path.exists(pp) or os.path.getsize(pp) != expected:
                    raise RuntimeError(f"Download part {i + 1} is incomplete.")
                with open(pp, "rb") as f:
                    shutil.copyfileobj(f, out, 1024 * 1024)
        os.replace(temp, self.path)
        shutil.rmtree(part_dir, ignore_errors=True)

    def _part(self, i, start, end, part_dir):
        pp = os.path.join(part_dir, f"part_{i}.bin")
        expected_size = end - start + 1
        for attempt in range(MAX_RETRIES):
            if self._stop.is_set() or self._worker_failed.is_set(): return
            have = min(os.path.getsize(pp), expected_size) if os.path.exists(pp) else 0
            if have >= expected_size:
                return
            pos = start + have
            try:
                headers = {"Range": f"bytes={pos}-{end}"}
                with self._request_retry("GET", headers=headers, stream=True) as r:
                    if r.status_code != 206:
                        raise RuntimeError(f"Server did not honor byte range for part {i + 1} (HTTP {r.status_code}).")
                    cr = r.headers.get("Content-Range", "")
                    m = re.match(r"^bytes\s+(\d+)-(\d+)/(\d+|\*)$", cr.strip(), re.I)
                    if not m or int(m.group(1)) != pos or int(m.group(2)) > end:
                        raise RuntimeError(f"Server returned an invalid Content-Range for part {i + 1}.")
                    if m.group(3) != "*" and int(m.group(3)) != self.total:
                        raise RuntimeError(f"Server changed file size during part {i + 1}.")
                    expected_response = int(m.group(2)) - int(m.group(1)) + 1
                    with open(pp, "ab") as f:
                        received = 0
                        for data in r.iter_content(self.chunk_size):
                            if self._stop.is_set() or self._worker_failed.is_set(): return
                            if not data:
                                continue
                            remaining = expected_response - received
                            if remaining <= 0:
                                break
                            if len(data) > remaining:
                                data = data[:remaining]
                            self._write_chunk(f, data)
                            received += len(data)
                    if received != expected_response:
                        raise RuntimeError(f"Part {i + 1} ended early ({received}/{expected_response} bytes).")
                if os.path.getsize(pp) == expected_size:
                    return
                raise RuntimeError(f"Part {i + 1} ended early ({os.path.getsize(pp)}/{expected_size} bytes).")
            except Exception as exc:
                if attempt + 1 < MAX_RETRIES:
                    time.sleep(min(8.0, 0.6 * (2 ** attempt)))
                    continue
                with self._lock:
                    self._worker_error = human_error(exc)
                self._worker_failed.set()
                return

    def _metrics(self):
        now = time.monotonic()
        dt = now - self._last_time
        if dt < 0.5: return False
        with self._lock:
            delta = self.downloaded - self._last_bytes
            self.speed = max(0, delta / dt)
            self._last_bytes = self.downloaded
            self._last_time = now
            self.eta = int(max(0, (self.total - self.downloaded) / self.speed)) if self.speed > 0 and self.total else None
        return True


class _WebpageURL(Exception):
    pass
