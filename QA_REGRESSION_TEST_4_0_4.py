import hashlib, os, sys, tempfile, threading, time, types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Headless Qt shim for downloader engine regression tests.
qt = types.ModuleType('PySide6.QtCore')
class Signal:
    def __init__(self,*a,**k): pass
    def connect(self,*a,**k): pass
    def emit(self,*a,**k): pass
class QObject: pass
qt.Signal=Signal; qt.QObject=QObject
pyside=types.ModuleType('PySide6'); pyside_qt=types.ModuleType('PySide6.QtCore')
pyside_qt.Signal=Signal; pyside_qt.QObject=QObject
sys.modules['PySide6']=pyside; sys.modules['PySide6.QtCore']=pyside_qt
sys.path.insert(0, os.path.dirname(__file__))
from downloader import DownloadTask

PDF = b"%PDF-1.7\n% DownGo certification PDF\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n" + os.urandom(128 * 1024)
BIN = os.urandom(2 * 1024 * 1024 + 777)

class Handler(BaseHTTPRequestHandler):
    def _send(self, data, ctype, ranged=True, filename=None):
        rng=self.headers.get('Range') if ranged else None
        start,end=0,len(data)-1
        if rng:
            try:
                unit,spec=rng.split('=',1)
                if unit != 'bytes': raise ValueError
                a,b=(spec.split('-',1)+[''])[:2]
                start=int(a or 0); end=int(b or end)
                if start >= len(data):
                    self.send_response(416); self.send_header('Content-Range',f'bytes */{len(data)}'); self.end_headers(); return
                end=min(end,len(data)-1)
            except Exception:
                self.send_response(416); self.end_headers(); return
            self.send_response(206); self.send_header('Content-Range',f'bytes {start}-{end}/{len(data)}')
        else:
            self.send_response(200)
        body=data[start:end+1]
        self.send_header('Content-Length',str(len(body))); self.send_header('Content-Type',ctype)
        if ranged: self.send_header('Accept-Ranges','bytes')
        if filename: self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        self.end_headers()
        if self.command == 'GET': self.wfile.write(body)
    def do_HEAD(self):
        path=self.path.split('?',1)[0]
        if path == '/pdf.pdf': self._send(PDF,'application/pdf',True,'certification.pdf')
        elif path == '/pdf-no-range': self._send(PDF,'application/pdf',False,'certification.pdf')
        elif path == '/redirect.pdf': self.send_response(302); self.send_header('Location','/pdf.pdf'); self.end_headers()
        elif path == '/html': self._send(b'<html><body>Not a file</body></html>','text/html',False,'page.html')
        elif path == '/404.pdf': self.send_response(404); self.end_headers()
        else: self.send_response(404); self.end_headers()
    def do_GET(self):
        path=self.path.split('?',1)[0]
        if path == '/pdf.pdf': self._send(PDF,'application/pdf',True,'certification.pdf')
        elif path == '/pdf-no-range': self._send(PDF,'application/pdf',False,'certification.pdf')
        elif path == '/redirect.pdf': self.send_response(302); self.send_header('Location','/pdf.pdf'); self.end_headers()
        elif path == '/html': self._send(b'<html><body>Not a file</body></html>','text/html',False,'page.html')
        elif path == '/404.pdf': self.send_response(404); self.end_headers()
        else: self.send_response(404); self.end_headers()
    def log_message(self,*a): pass

srv=ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=srv.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{srv.server_port}'

def run(url, name, connections=4):
    td=tempfile.TemporaryDirectory()
    t=DownloadTask(name,url,td.name,connections=connections,enable_scan=False)
    t.start()
    deadline=time.time()+15
    while time.time()<deadline and t.status not in ('Completed','Error','Cancelled'):
        time.sleep(.05)
    if t.status != 'Completed':
        raise AssertionError(f'{name}: {t.status}: {t.error}')
    return td,t

try:
    td,t=run(base+'/pdf.pdf','pdf',4)
    assert t.filename.lower().endswith('.pdf'), t.filename
    assert Path(t.path).read_bytes()==PDF
    td.cleanup(); print('PASS PDF range + filename + SHA')

    td,t=run(base+'/pdf-no-range','pdf-fallback',4)
    assert t.filename.lower().endswith('.pdf'), t.filename
    assert Path(t.path).read_bytes()==PDF
    td.cleanup(); print('PASS PDF no-range single fallback')

    td,t=run(base+'/redirect.pdf','redirect',4)
    assert Path(t.path).read_bytes()==PDF
    td.cleanup(); print('PASS redirect PDF')

    td=tempfile.TemporaryDirectory(); t=DownloadTask('html',base+'/html',td.name,connections=4,enable_scan=False); t.start()
    deadline=time.time()+10
    while time.time()<deadline and t.status not in ('Completed','Error','Cancelled'): time.sleep(.05)
    assert t.status=='Error' and 'webpage' in t.error.lower(), (t.status,t.error)
    td.cleanup(); print('PASS HTML page rejected cleanly')

    td=tempfile.TemporaryDirectory(); t=DownloadTask('404',base+'/404.pdf',td.name,connections=4,enable_scan=False); t.start()
    deadline=time.time()+10
    while time.time()<deadline and t.status not in ('Completed','Error','Cancelled'): time.sleep(.05)
    assert t.status=='Error' and '404' in t.error, (t.status,t.error)
    td.cleanup(); print('PASS HTTP 404 clean error')

    print('ALL REGRESSION TESTS PASSED')
finally:
    srv.shutdown(); srv.server_close()
