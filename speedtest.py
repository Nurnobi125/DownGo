"""DownGo network speed test engine.

Uses public test endpoints with short bounded transfers and safe fallbacks.
The UI layer owns Qt signals; this module stays framework-light.
"""
from __future__ import annotations

import time
import requests

USER_AGENT = "DownGo/4.0.7 SpeedTest"
DOWNLOAD_ENDPOINTS = (
    "https://speed.cloudflare.com/__down?bytes=25000000",
    "https://fsn1-speed.hetzner.com/100MB.bin",
)
UPLOAD_ENDPOINTS = (
    "https://speed.cloudflare.com/__up",
)
PING_ENDPOINTS = (
    "https://www.google.com/generate_204",
    "https://www.cloudflare.com/cdn-cgi/trace",
    "https://www.microsoft.com/",
)


class SpeedTestEngine:
    """Measures latency, download speed, and upload speed with fallbacks."""

    @staticmethod
    def _session():
        s = requests.Session()
        s.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*", "Accept-Encoding": "identity"})
        return s

    @staticmethod
    def measure_ping(host=None):
        endpoints = (host,) if host else PING_ENDPOINTS
        for endpoint in endpoints:
            try:
                start = time.perf_counter()
                with SpeedTestEngine._session() as s:
                    r = s.get(endpoint, timeout=(3, 5), stream=True)
                    r.close()
                return round((time.perf_counter() - start) * 1000, 2)
            except requests.RequestException:
                continue
        return -1

    @staticmethod
    def measure_download_speed(test_url=None, duration=5):
        endpoints = (test_url,) if test_url else DOWNLOAD_ENDPOINTS
        last_error = None
        for endpoint in endpoints:
            try:
                start = time.perf_counter()
                downloaded = 0
                with SpeedTestEngine._session() as s:
                    with s.get(endpoint, stream=True, timeout=(5, 15), allow_redirects=True) as r:
                        r.raise_for_status()
                        for chunk in r.iter_content(chunk_size=256 * 1024):
                            if chunk:
                                downloaded += len(chunk)
                            if time.perf_counter() - start >= duration:
                                break
                elapsed = max(time.perf_counter() - start, 0.001)
                if downloaded > 0:
                    return round((downloaded * 8 / elapsed) / 1_000_000, 2)
                last_error = "No bytes received"
            except requests.RequestException as exc:
                last_error = exc
                continue
        return 0.0

    @staticmethod
    def measure_upload_speed(test_url=None, size_mb=2):
        endpoints = (test_url,) if test_url else UPLOAD_ENDPOINTS
        payload = b"0" * (max(1, int(size_mb)) * 1024 * 1024)
        for endpoint in endpoints:
            try:
                start = time.perf_counter()
                with SpeedTestEngine._session() as s:
                    r = s.post(endpoint, data=payload, timeout=(5, 20), allow_redirects=True)
                    r.raise_for_status()
                elapsed = max(time.perf_counter() - start, 0.001)
                return round((len(payload) * 8 / elapsed) / 1_000_000, 2)
            except requests.RequestException:
                continue
        return 0.0
