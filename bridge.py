import json, queue, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from downloader import validate_url

class BridgeServer:
    def __init__(self,on_add,host="127.0.0.1",port=8765):
        self.host=host; self.port=port; self.on_add=on_add; self.server=None; self.thread=None
    def start(self):
        parent=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*_): pass
            def _headers(self):
                self.send_header("Access-Control-Allow-Origin","*")
                self.send_header("Access-Control-Allow-Methods","POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers","Content-Type")
                self.send_header("Cache-Control","no-store")
            def do_OPTIONS(self): self.send_response(204); self._headers(); self.end_headers()
            def do_GET(self):
                if urlparse(self.path).path=="/health":
                    body=json.dumps({"ok":True,"service":"DownGo Bridge","version":"4.0.7"}).encode()
                    self.send_response(200); self._headers(); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body); return
                self.send_response(404); self._headers(); self.end_headers()
            def do_POST(self):
                if urlparse(self.path).path!="/add": self.send_response(404); self._headers(); self.end_headers(); return
                try:
                    length=max(0,min(int(self.headers.get("Content-Length","0")),1024*1024)); data=json.loads(self.rfile.read(length).decode("utf-8"))
                    url=validate_url(str(data.get("url","")).strip())
                    q=queue.Queue(maxsize=1); req={"url":url,"filename":str(data.get("filename","")).strip(),"referrer":str(data.get("referrer","")).strip(),"result":q}
                    parent.on_add(req)
                    try: result=q.get(timeout=5)
                    except queue.Empty: result={"accepted":False,"error":"DownGo did not respond in time."}
                    body=json.dumps(result).encode(); self.send_response(200 if result.get("accepted") else 503); self._headers(); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
                except Exception as e:
                    body=json.dumps({"accepted":False,"error":str(e)}).encode(); self.send_response(400); self._headers(); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
        self.server=ThreadingHTTPServer((self.host,self.port),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,name="DownGo-Bridge",daemon=True); self.thread.start()
    def stop(self):
        if self.server:
            self.server.shutdown(); self.server.server_close(); self.server=None
