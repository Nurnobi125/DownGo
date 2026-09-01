"""Headless regression tests for DownGo's file handling.
Runs without PySide6 by testing downloader helpers and a local HTTP server.
"""
from __future__ import annotations
import hashlib, os, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from downloader import DownloadTask, get_file_type_info

DATA = {
    "sample.pdf": b"%PDF-1.4\n% DownGo test PDF\n%%EOF\n",
    "sample.mp3": b"ID3" + bytes(range(256)) * 64,
    "sample.mp4": b"\x00\x00\x00\x18ftypmp42" + bytes(range(256)) * 128,
    "sample.zip": b"PK\x03\x04" + bytes(range(256)) * 128,
    "sample.jpg": b"\xff\xd8\xff\xe0" + bytes(range(256)) * 64,
    "sample.png": b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 64,
    "sample.txt": b"DownGo certification text test\n" * 100,
}

class Handler(BaseHTTPRequestHandler):
    def do_HEAD(self): self._serve(head=True)
    def do_GET(self): self._serve(head=False)
    def _serve(self, head=False):
        name = self.path.lstrip('/').split('?',1)[0]
        data = DATA.get(name)
        if data is None:
            self.send_response(404); self.end_headers(); return
        start, end = 0, len(data)-1
        rng = self.headers.get('Range')
        if rng and rng.startswith('bytes='):
            spec = rng[6:].split('-',1)
            start = int(spec[0] or 0); end = int(spec[1]) if len(spec)>1 and spec[1] else end
            end = min(end, len(data)-1)
            self.send_response(206)
            self.send_header('Content-Range', f'bytes {start}-{end}/{len(data)}')
        else:
            self.send_response(200)
        self.send_header('Content-Length', str(end-start+1))
        self.send_header('Content-Type', {'sample.pdf':'application/pdf','sample.mp3':'audio/mpeg','sample.mp4':'video/mp4','sample.zip':'application/zip','sample.jpg':'image/jpeg','sample.png':'image/png','sample.txt':'text/plain'}[name])
        self.send_header('Content-Disposition', f'attachment; filename="{name}"')
        self.end_headers()
        if not head: self.wfile.write(data[start:end+1])
    def log_message(self, *_): pass

srv = ThreadingHTTPServer(('127.0.0.1',0), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
root = Path(tempfile.mkdtemp(prefix='downgo_qa_'))
try:
    base = f'http://127.0.0.1:{srv.server_port}'
    for name in DATA:
        task = DownloadTask(name, f'{base}/{name}', str(root), connections=4)
        task.start()
        # Poll because DownloadTask is intentionally asynchronous.
        import time
        deadline=time.time()+10
        while task.status not in ('Completed','Error','Cancelled') and time.time()<deadline: time.sleep(.02)
        assert task.status == 'Completed', (name, task.status, task.error)
        assert Path(task.path).read_bytes() == DATA[name], name
        assert task.sha256 == hashlib.sha256(DATA[name]).hexdigest(), name
        print('PASS', name, get_file_type_info(name)[1], task.connections)
    print('ALL FILE TYPE TESTS PASSED')
finally:
    srv.shutdown(); srv.server_close()
