import time
import requests

class SpeedTestEngine:
    """Measures latency, download speed, and upload speed."""
    
    @staticmethod
    def measure_ping(host="https://www.google.com"):
        try:
            start = time.time()
            requests.head(host, timeout=(3, 3))
            return round((time.time() - start) * 1000, 2)
        except Exception:
            return -1

    @staticmethod
    def measure_download_speed(test_url="https://speed.cloudflare.com/__down?bytes=25000000", duration=5):
        """Downloads a test payload for a fixed duration to estimate speed in Mbps."""
        try:
            start_time = time.time()
            downloaded = 0
            with requests.get(test_url, stream=True, timeout=(3, 5)) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=64 * 1024):
                    downloaded += len(chunk)
                    if time.time() - start_time >= duration:
                        break
            elapsed = time.time() - start_time
            bps = (downloaded * 8) / elapsed
            return round(bps / 1_000_000, 2)
        except Exception:
            return 0.0

    @staticmethod
    def measure_upload_speed(test_url="https://speed.cloudflare.com/__up", size_mb=2):
        """Uploads a dummy payload to measure upload bandwidth in Mbps."""
        try:
            payload = b"0" * (size_mb * 1024 * 1024)
            start_time = time.time()
            r = requests.post(test_url, data=payload, timeout=(3, 10))
            r.raise_for_status()
            elapsed = time.time() - start_time
            bps = (len(payload) * 8) / elapsed
            return round(bps / 1_000_000, 2)
        except Exception:
            return 0.0