import json
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


class BridgeServer:
    def __init__(self, on_add, host="127.0.0.1", port=8765):
        self.host = host
        self.port = port
        self.on_add = on_add
        self.server = None
        self.thread = None

    def start(self):
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                return

            def _headers(self):
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Cache-Control", "no-store")

            def do_OPTIONS(self):
                self.send_response(204)
                self._headers()
                self.end_headers()

            def do_GET(self):
                if urlparse(self.path).path == "/health":
                    body = json.dumps({"ok": True, "service": "DownGo Bridge"}).encode()
                    self.send_response(200)
                    self._headers()
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return

                self.send_response(404)
                self._headers()
                self.end_headers()

            def do_POST(self):
                path = urlparse(self.path).path

                if path != "/add":
                    self.send_response(404)
                    self._headers()
                    self.end_headers()
                    return

                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    raw = self.rfile.read(length)
                    data = json.loads(raw.decode("utf-8"))

                    url = str(data.get("url", "")).strip()
                    if not (url.startswith("http://") or url.startswith("https://")):
                        raise ValueError("Only HTTP/HTTPS URLs are supported.")

                    result_q = queue.Queue(maxsize=1)
                    request = {
                        "url": url,
                        "filename": str(data.get("filename", "")).strip(),
                        "referrer": str(data.get("referrer", "")).strip(),
                        "result": result_q,
                    }

                    parent.on_add(request)
                    try:
                        result = result_q.get(timeout=4)
                    except queue.Empty:
                        result = {"accepted": False, "error": "DownGo did not respond in time."}

                    body = json.dumps(result).encode("utf-8")
                    self.send_response(200 if result.get("accepted") else 503)
                    self._headers()
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)

                except Exception as e:
                    body = json.dumps({"accepted": False, "error": str(e)}).encode()
                    self.send_response(400)
                    self._headers()
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)

        try:
            self.server = ThreadingHTTPServer((self.host, self.port), Handler)
        except OSError as e:
            raise RuntimeError(f"Could not start local bridge on {self.host}:{self.port}: {e}")

        self.thread = threading.Thread(
            target=self.server.serve_forever,
            name="DownGo-Bridge",
            daemon=True
        )
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
