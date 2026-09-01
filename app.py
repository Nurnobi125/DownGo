import json
import os
import sys
import threading
import uuid
import webbrowser
import requests
import zipfile
import subprocess
import hmac
import hashlib
from pathlib import Path
import queue

from PySide6.QtCore import Qt, QTimer, QObject, Signal, QTime, QPropertyAnimation, QEasingCurve, QThread
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor, QLinearGradient, QFont, QClipboard
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QFileDialog, QSpinBox, QLabel, QFrame,
    QSystemTrayIcon, QMenu, QMessageBox, QHeaderView, QDialog,
    QAbstractItemView, QCheckBox, QProgressBar, QRadioButton, QButtonGroup, QTextEdit,
    QProgressDialog, QInputDialog, QComboBox, QColorDialog, QListWidget, QTimeEdit, QSplitter,
    QGraphicsOpacityEffect
)

from downloader import DownloadTask, get_file_type_info, validate_url, check_resume_capability
from speedtest import SpeedTestEngine
from bridge import BridgeServer
from updater import UpdateCheckThread, InstallerDownloadThread, launch_installer_and_exit, CURRENT_VERSION

APP_DIR = Path.home() / ".mini_idm"
APP_DIR.mkdir(exist_ok=True)
HISTORY = APP_DIR / "queue.json"
LICENSE_FILE = APP_DIR / "license_config.json"
UI_SETTINGS_FILE = APP_DIR / "ui_settings.json"
LITE_MODE_DEFAULT = False

# The MSIX build script drops this marker beside DownGo.exe. Store builds
# should not self-update by downloading an external installer; Microsoft Store
# manages package updates.
STORE_BUILD = (Path(sys.executable).resolve().parent / "store_build.json").exists()

# Developer/QA unlock is opt-in via environment variables only — it is never
# hardcoded and never shown in a normal build.
# --- Premium Refined Themes ---
THEMES = {
    "Dark Mode": """
        QMainWindow, QWidget { background: #0d1117; color: #c9d1d9; font-family: 'Segoe UI', Arial; }
        QLineEdit, QSpinBox, QTextEdit, QComboBox, QTimeEdit { background: #161b22; border: 1px solid #30363d; color: #f0f6fc; padding: 6px; border-radius: 6px; }
        QPushButton { background: #21262d; border: 1px solid #30363d; color: #c9d1d9; padding: 6px 14px; border-radius: 6px; font-weight: 600; }
        QPushButton:hover { background: #30363d; border-color: #8b949e; color: #ffffff; }
        QPushButton#add { background: #238636; border-color: #2ea043; color: #ffffff; }
        QPushButton#add:hover { background: #2ea043; }
        QPushButton#dev { background: #1f6beb; border-color: #388bfd; color: #ffffff; }
        QTableWidget { background: #0d1117; border: 1px solid #21262d; gridline-color: transparent; color: #c9d1d9; font-family: 'Consolas', 'Fira Code', monospace; font-size: 12px; }
        QTableWidget::item { padding: 6px; border-bottom: 1px solid #161b22; }
        QTableWidget::item:selected { background-color: #1f242c; color: #58a6ff; }
        QListWidget { background: #161b22; border: 1px solid #21262d; color: #c9d1d9; border-radius: 6px; }
        QListWidget::item { padding: 8px; border-radius: 4px; }
        QListWidget::item:selected { background: #1f6beb; color: #ffffff; font-weight: bold; }
        QHeaderView::section { background: #161b22; color: #8b949e; border: none; border-bottom: 1px solid #30363d; padding: 6px; font-weight: 600; }
        QLabel#title { color: #58a6ff; font-size: 16px; font-weight: bold; }
        QLabel#muted { color: #8b949e; }
    """,
    "Hacker Terminal": """
        QMainWindow, QWidget { background: #020b02; color: #00ff00; font-family: 'Consolas', 'Courier New'; }
        QLineEdit, QSpinBox, QTextEdit, QComboBox, QTimeEdit { background: #001100; border: 1px solid #00ff00; color: #00ff00; padding: 6px; }
        QPushButton { background: #002200; border: 1px solid #00ff00; color: #00ff00; padding: 6px 12px; font-weight: bold; }
        QPushButton:hover { background: #00ff00; color: #000000; }
        QPushButton#add { background: #003300; border-color: #00ff00; color: #00ff00; }
        QTableWidget { background: #000800; border: 1px solid #00ff00; gridline-color: #003300; color: #00ff00; font-family: 'Consolas', monospace; }
        QListWidget { background: #000800; border: 1px solid #00ff00; color: #00ff00; }
        QListWidget::item:selected { background: #00ff00; color: #000000; }
        QHeaderView::section { background: #001a00; color: #00ff00; border: 1px solid #00ff00; }
        QLabel#title { color: #00ff00; font-size: 16px; font-weight: bold; }
        QLabel#muted { color: #00aa00; }
    """,
    "Linux Matrix": """
        QMainWindow, QWidget { background: #181923; color: #f8f8f2; font-family: 'Ubuntu', Arial; }
        QLineEdit, QSpinBox, QTextEdit, QComboBox, QTimeEdit { background: #21222c; border: 1px solid #6272a4; color: #f8f8f2; padding: 6px; border-radius: 4px; }
        QPushButton { background: #282a36; border: 1px solid #6272a4; color: #50fa7b; padding: 6px 12px; border-radius: 4px; font-weight: bold; }
        QPushButton:hover { background: #44475a; border-color: #50fa7b; }
        QPushButton#add { background: #213627; border-color: #50fa7b; color: #50fa7b; }
        QTableWidget, QListWidget { background: #21222c; border: 1px solid #44475a; gridline-color: #282a36; font-family: 'Consolas', monospace; }
        QListWidget::item:selected { background: #44475a; color: #50fa7b; }
        QHeaderView::section { background: #282a36; color: #8be9fd; border: 0; }
        QLabel#title { color: #50fa7b; font-size: 16px; font-weight: bold; }
        QLabel#muted { color: #6272a4; }
    """,
    "Luxury Gold": """
        QMainWindow, QWidget { background: #0f0f0f; color: #f1e5ac; font-family: 'Segoe UI', Arial; }
        QLineEdit, QSpinBox, QTextEdit, QComboBox, QTimeEdit { background: #1a1a1a; border: 1px solid #d4af37; color: #fff8dc; padding: 6px; border-radius: 4px; }
        QPushButton { background: #242424; border: 1px solid #d4af37; color: #d4af37; padding: 6px 12px; border-radius: 4px; font-weight: bold; }
        QPushButton:hover { background: #d4af37; color: #000000; }
        QPushButton#add { background: #3a320d; border-color: #ffd700; color: #ffd700; }
        QTableWidget, QListWidget { background: #141414; border: 1px solid #8b7500; gridline-color: #262626; font-family: 'Consolas', monospace; }
        QListWidget::item:selected { background: #d4af37; color: #000000; }
        QHeaderView::section { background: #1f1f1f; color: #ffd700; border: 0; }
        QLabel#title { color: #ffd700; font-size: 16px; font-weight: bold; }
        QLabel#muted { color: #998a46; }
    """,
    "Glass UI": """
        QMainWindow, QWidget { background: rgba(15, 23, 42, 0.85); color: #e2e8f0; font-family: 'Segoe UI', Arial; }
        QLineEdit, QSpinBox, QTextEdit, QComboBox, QTimeEdit { background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255, 255, 255, 0.15); color: #f8fafc; padding: 6px; border-radius: 6px; }
        QPushButton { background: rgba(51, 65, 85, 0.5); border: 1px solid rgba(255, 255, 255, 0.2); color: #38bdf8; padding: 6px 12px; border-radius: 6px; font-weight: bold; }
        QPushButton:hover { background: rgba(56, 189, 248, 0.2); border-color: #38bdf8; }
        QPushButton#add { background: rgba(14, 116, 144, 0.5); border-color: #06b6d4; color: #67e8f9; }
        QTableWidget, QListWidget { background: rgba(15, 23, 42, 0.5); border: 1px solid rgba(255, 255, 255, 0.1); gridline-color: rgba(255, 255, 255, 0.05); font-family: 'Consolas', monospace; }
        QListWidget::item:selected { background: rgba(56, 189, 248, 0.3); color: #38bdf8; }
        QHeaderView::section { background: rgba(30, 41, 59, 0.8); color: #38bdf8; border: 0; }
        QLabel#title { color: #38bdf8; font-size: 16px; font-weight: bold; }
        QLabel#muted { color: #94a3b8; }
    """,
    "Aurora Glass": """
        QMainWindow, QWidget { background: transparent; color: #2b2140; font-family: 'Segoe UI', Arial; }
        QLineEdit, QSpinBox, QTextEdit, QComboBox, QTimeEdit {
            background: rgba(255, 255, 255, 0.38);
            border: 1px solid rgba(255, 255, 255, 0.55);
            color: #2b2140; padding: 7px; border-radius: 10px;
        }
        QPushButton {
            background: rgba(255, 255, 255, 0.30);
            border: 1px solid rgba(255, 255, 255, 0.55);
            color: #3d2c66; padding: 7px 14px; border-radius: 10px; font-weight: 600;
        }
        QPushButton:hover { background: rgba(255, 255, 255, 0.5); border-color: #ffffff; }
        QPushButton#add {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(255,154,158,0.75), stop:1 rgba(255,206,140,0.75));
            border-color: rgba(255,255,255,0.7); color: #3d1f1f;
        }
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(161,140,255,0.75), stop:1 rgba(255,159,243,0.75));
            border-color: rgba(255,255,255,0.7); color: #2c1a4d;
        }
        QPushButton#dev { background: rgba(140, 200, 255, 0.35); border-color: rgba(255,255,255,0.6); color: #1a3a5c; }
        QTableWidget {
            background: rgba(255, 255, 255, 0.22);
            border: 1px solid rgba(255, 255, 255, 0.45);
            border-radius: 10px; gridline-color: rgba(255,255,255,0.15);
            color: #2b2140; font-family: 'Consolas', 'Fira Code', monospace; font-size: 12px;
        }
        QTableWidget::item { padding: 6px; border-bottom: 1px solid rgba(255,255,255,0.15); }
        QTableWidget::item:selected { background-color: rgba(161,140,255,0.35); color: #2c1a4d; }
        QListWidget {
            background: rgba(255, 255, 255, 0.25); border: 1px solid rgba(255,255,255,0.5);
            color: #2b2140; border-radius: 10px;
        }
        QListWidget::item { padding: 8px; border-radius: 6px; }
        QListWidget::item:selected { background: rgba(161,140,255,0.55); color: #1f1235; font-weight: bold; }
        QHeaderView::section {
            background: rgba(255,255,255,0.3); color: #4a3a6b; border: none;
            border-bottom: 1px solid rgba(255,255,255,0.4); padding: 6px; font-weight: 600; border-radius: 0px;
        }
        QLabel#title { color: #6d3fae; font-size: 16px; font-weight: bold; }
        QLabel#muted { color: #5c5372; }
        QSplitter::handle { background: rgba(255,255,255,0.2); }
    """,
    "Frosted Glass": """
        QMainWindow, QWidget { background: rgba(255, 255, 255, 0.1); color: #0f172a; font-family: 'Segoe UI', Arial; }
        QLineEdit, QSpinBox, QTextEdit, QComboBox, QTimeEdit { background: rgba(255, 255, 255, 0.5); border: 1px solid rgba(0, 0, 0, 0.1); color: #0f172a; padding: 6px; border-radius: 6px; }
        QPushButton { background: rgba(255, 255, 255, 0.4); border: 1px solid rgba(0, 0, 0, 0.15); color: #0284c7; padding: 6px 12px; border-radius: 6px; font-weight: bold; }
        QPushButton:hover { background: rgba(2, 132, 199, 0.15); border-color: #0284c7; }
        QPushButton#add { background: rgba(186, 230, 253, 0.6); border-color: #0284c7; color: #0369a1; }
        QTableWidget, QListWidget { background: rgba(255, 255, 255, 0.3); border: 1px solid rgba(0, 0, 0, 0.08); gridline-color: rgba(0, 0, 0, 0.05); font-family: 'Consolas', monospace; }
        QListWidget::item:selected { background: rgba(2, 132, 199, 0.2); color: #0369a1; }
        QHeaderView::section { background: rgba(241, 245, 249, 0.7); color: #0369a1; border: 0; }
        QLabel#title { color: #0284c7; font-size: 16px; font-weight: bold; }
        QLabel#muted { color: #64748b; }
    """,
    "iOS Glass": """
        QMainWindow, QWidget { background: rgba(242, 246, 252, 0.92); color: #1c1c1e; font-family: -apple-system, 'Segoe UI', Arial; }
        QLineEdit, QSpinBox, QTextEdit, QComboBox, QTimeEdit { background: rgba(255, 255, 255, 0.75); border: 1px solid rgba(60, 60, 67, 0.15); color: #1c1c1e; padding: 7px; border-radius: 10px; }
        QPushButton { background: rgba(255, 255, 255, 0.65); border: 1px solid rgba(60, 60, 67, 0.12); color: #007aff; padding: 7px 14px; border-radius: 10px; font-weight: 600; }
        QPushButton:hover { background: rgba(0, 122, 255, 0.12); border-color: #007aff; }
        QPushButton#add { background: rgba(52, 199, 89, 0.18); border-color: #34c759; color: #1e7e34; }
        QTableWidget, QListWidget { background: rgba(255, 255, 255, 0.55); border: 1px solid rgba(60, 60, 67, 0.1); gridline-color: rgba(60, 60, 67, 0.06); border-radius: 10px; font-family: 'SF Mono', 'Consolas', monospace; }
        QListWidget::item { padding: 8px; border-radius: 8px; }
        QListWidget::item:selected { background: rgba(0, 122, 255, 0.16); color: #007aff; font-weight: 600; }
        QHeaderView::section { background: rgba(255, 255, 255, 0.7); color: #6e6e73; border: 0; padding: 6px; font-weight: 600; }
        QLabel#title { color: #007aff; font-size: 16px; font-weight: 700; }
        QLabel#muted { color: #6e6e73; }
    """,
    "Cyberpunk Neon": """
        QMainWindow, QWidget { background: #0a0014; color: #f5d0ff; font-family: 'Segoe UI', Arial; }
        QLineEdit, QSpinBox, QTextEdit, QComboBox, QTimeEdit { background: #150022; border: 1px solid #ff2ec4; color: #baffff; padding: 6px; border-radius: 6px; }
        QPushButton { background: #1a0028; border: 1px solid #00f0ff; color: #00f0ff; padding: 6px 12px; border-radius: 6px; font-weight: bold; }
        QPushButton:hover { background: #00f0ff; color: #0a0014; }
        QPushButton#add { background: #001f1a; border-color: #00ffab; color: #00ffab; }
        QTableWidget, QListWidget { background: #10001d; border: 1px solid #ff2ec4; gridline-color: #23003b; color: #baffff; font-family: 'Consolas', monospace; }
        QListWidget::item:selected { background: #ff2ec4; color: #0a0014; font-weight: bold; }
        QHeaderView::section { background: #1a0028; color: #ff2ec4; border: 1px solid #ff2ec4; font-weight: 600; }
        QLabel#title { color: #00f0ff; font-size: 16px; font-weight: bold; }
        QLabel#muted { color: #b06ad1; }
    """
}

# --- Helpers ---
def load_ui_settings():
    try:
        if UI_SETTINGS_FILE.exists():
            return json.loads(UI_SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def save_ui_settings(data):
    try:
        UI_SETTINGS_FILE.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass

def human(n):
    n = float(n or 0)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PB"

def eta_text(s):
    if s is None:
        return "--:--"
    s = int(s)
    return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"

def make_icon():
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor("#0d1117"))
    p.setPen(QColor("#00e5ff"))
    p.drawRoundedRect(4, 4, 56, 56, 12, 12)
    p.setFont(QFont("Segoe UI", 25, QFont.Bold))
    p.drawText(pm.rect(), Qt.AlignCenter, "↓")
    p.end()
    return QIcon(pm)

class SpeedTestSignals(QObject):
    update = Signal(str, str)
    finished = Signal()


class SpeedTestModal(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Internet Speed Test — DownGo")
        self.setFixedSize(420, 280)
        
        self.setStyleSheet("""
            QDialog { background-color: #0d1117; color: #c9d1d9; }
            QLabel { color: #c9d1d9; font-size: 13px; }
            QLabel#title { color: #58a6ff; font-size: 16px; font-weight: bold; }
            QPushButton { background-color: #1f6beb; border: 1px solid #388bfd; color: #ffffff; padding: 8px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #388bfd; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        title = QLabel("⚡ Internet Speed & Latency Benchmark")
        title.setObjectName("title")
        layout.addWidget(title)

        self.lbl_ping = QLabel("Ping: Ready")
        self.lbl_down = QLabel("Download Speed: Ready")
        self.lbl_up = QLabel("Upload Speed: Ready")

        layout.addWidget(self.lbl_ping)
        layout.addWidget(self.lbl_down)
        layout.addWidget(self.lbl_up)

        self.btn_run = QPushButton("⚡ START SPEED TEST")
        self.btn_run.setObjectName("speedtest")
        self.btn_run.clicked.connect(self._run_test)
        self.signals = SpeedTestSignals()
        self.signals.update.connect(self._apply_update)
        self.signals.finished.connect(self._test_finished)
        layout.addWidget(self.btn_run)

    def _run_test(self):
        self.btn_run.setEnabled(False)
        self.btn_run.setText("Testing connection...")
        threading.Thread(target=self._test_thread, daemon=True).start()

    def _apply_update(self, target, value):
        mapping = {"ping": self.lbl_ping, "down": self.lbl_down, "up": self.lbl_up}
        label = mapping.get(target)
        if label is not None:
            label.setText(value)

    def _test_finished(self):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("⚡ RUN AGAIN")

    def _test_thread(self):
        self.signals.update.emit("ping", "Ping: Testing...")
        ping = SpeedTestEngine.measure_ping()
        self.signals.update.emit("ping", f"Ping: {ping} ms" if ping >= 0 else "Ping: Failed")

        self.signals.update.emit("down", "Download Speed: Testing...")
        down = SpeedTestEngine.measure_download_speed()
        self.signals.update.emit("down", f"Download Speed: {down} Mbps")

        self.signals.update.emit("up", "Upload Speed: Testing...")
        up = SpeedTestEngine.measure_upload_speed()
        self.signals.update.emit("up", f"Upload Speed: {up} Mbps")
        self.signals.finished.emit()

class BatchImportModal(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Link Importer — DownGo")
        self.setFixedSize(500, 380)
        self.urls = []

        self.setStyleSheet("""
            QDialog { background-color: #0d1117; color: #c9d1d9; }
            QLabel { color: #c9d1d9; }
            QTextEdit { background-color: #161b22; border: 1px solid #30363d; color: #f0f6fc; border-radius: 6px; }
            QPushButton { background-color: #21262d; border: 1px solid #30363d; color: #c9d1d9; padding: 6px 14px; border-radius: 6px; font-weight: 600; }
            QPushButton:hover { background-color: #30363d; color: #ffffff; }
            QPushButton#add { background-color: #238636; border-color: #2ea043; color: #ffffff; }
            QPushButton#add:hover { background-color: #2ea043; }
        """)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Paste multiple HTTP/HTTPS URLs (one per line):"))
        self.text_area = QTextEdit()
        layout.addWidget(self.text_area)

        btns = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_import = QPushButton("Import All")
        btn_import.setObjectName("add")
        btn_import.clicked.connect(self._submit)

        btns.addWidget(btn_cancel)
        btns.addWidget(btn_import)
        layout.addLayout(btns)

    def _submit(self):
        lines = self.text_area.toPlainText().splitlines()
        self.urls = [l.strip() for l in lines if l.strip().startswith(("http://", "https://"))]
        self.accept()

class BridgeSignals(QObject):
    request = Signal(object)

class DownloadProgressWindow(QWidget):
    def __init__(self, task, parent=None):
        super().__init__(None)
        self.task = task
        self.parent_app = parent
        self.setWindowTitle(f"Downloading: {task.filename}")
        self.setFixedWidth(540)
        if parent:
            self.setWindowIcon(parent.windowIcon())
        
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        self._build_ui()
        
        self.task.changed.connect(self.update_progress)
        self.task.finished.connect(self.on_finished)
        self.task.failed.connect(self.on_failed)
        
        self.update_progress()

    def _build_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #0d1117;
                color: #c9d1d9;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel { color: #c9d1d9; }
            QLabel#title { color: #58a6ff; font-size: 15px; font-weight: 600; }
            QPushButton {
                background-color: #21262d;
                border: 1px solid #30363d;
                color: #c9d1d9;
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #30363d; border-color: #8b949e; color: #ffffff; }
            QPushButton:disabled { background-color: #161b22; color: #484f58; border-color: #21262d; }
            QCheckBox { color: #8b949e; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        type_label, _ = get_file_type_info(self.task.filename)
        self.title_lbl = QLabel(f"{type_label} {self.task.filename}")
        self.title_lbl.setObjectName("title")
        self.title_lbl.setWordWrap(True)
        layout.addWidget(self.title_lbl)

        grid = QGridLayout()
        grid.setSpacing(6)
        
        grid.addWidget(QLabel("URL:"), 0, 0)
        url_text = self.task.url
        if len(url_text) > 65:
            url_text = url_text[:35] + "..." + url_text[-25:]
        self.url_lbl = QLabel(url_text)
        self.url_lbl.setStyleSheet("color: #8b949e;")
        self.url_lbl.setToolTip(self.task.url)
        grid.addWidget(self.url_lbl, 0, 1)

        grid.addWidget(QLabel("Save To:"), 1, 0)
        self.save_lbl = QLabel(self.task.path)
        self.save_lbl.setStyleSheet("color: #8b949e;")
        self.save_lbl.setWordWrap(True)
        grid.addWidget(self.save_lbl, 1, 1)

        grid.addWidget(QLabel("SHA-256:"), 2, 0)
        self.hash_lbl = QLabel("Calculating post-completion...")
        self.hash_lbl.setStyleSheet("color: #00e5ff; font-size: 11px;")
        grid.addWidget(self.hash_lbl, 2, 1)

        layout.addLayout(grid)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        layout.addWidget(self.bar)

        stats = QHBoxLayout()
        self.status_lbl = QLabel("Status: Connecting...")
        self.speed_lbl = QLabel("Speed: 0 B/s")
        self.eta_lbl = QLabel("ETA: --:--")
        stats.addWidget(self.status_lbl)
        stats.addWidget(self.speed_lbl)
        stats.addWidget(self.eta_lbl)
        layout.addLayout(stats)

        self.auto_close_cb = QCheckBox("Close this dialog when download completes")
        layout.addWidget(self.auto_close_cb)

        btns = QHBoxLayout()
        self.btn_pause = QPushButton("Pause")
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.cancel_download)
        self.btn_open = QPushButton("Open File")
        self.btn_open.setEnabled(False)
        self.btn_open.clicked.connect(self.open_file)
        self.btn_folder = QPushButton("Open Folder")
        self.btn_folder.setEnabled(False)
        self.btn_folder.clicked.connect(self.open_folder)
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.close)

        btns.addWidget(self.btn_pause)
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_open)
        btns.addWidget(self.btn_folder)
        btns.addWidget(self.btn_close)
        layout.addLayout(btns)

    def toggle_pause(self):
        if self.task.status == "Paused":
            self.task.resume()
            self.btn_pause.setText("Pause")
        elif self.task.status in ("Downloading", "Checking...", "Merging"):
            self.task.pause()
            self.btn_pause.setText("Resume")

    def cancel_download(self):
        self.task.cancel()
        self.status_lbl.setText("Status: Cancelled")
        self.btn_pause.setEnabled(False)
        self.btn_cancel.setEnabled(False)

    def open_file(self):
        if os.path.exists(self.task.path):
            try:
                os.startfile(os.path.abspath(self.task.path))
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not open file: {e}")

    def open_folder(self):
        if os.path.exists(self.task.path):
            try:
                import subprocess
                subprocess.Popen(["explorer.exe", "/select," + os.path.abspath(self.task.path)])
            except Exception:
                try:
                    os.startfile(os.path.dirname(os.path.abspath(self.task.path)))
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Could not open folder: {e}")

    def update_progress(self):
        type_label, _ = get_file_type_info(self.task.filename)
        self.title_lbl.setText(f"{type_label} {self.task.filename}")
        self.setWindowTitle(f"Downloading: {self.task.filename}")
        self.save_lbl.setText(self.task.path)
        
        pct = (self.task.downloaded / self.task.total * 100) if self.task.total else 0
        self.bar.setValue(int(pct))
        
        self.status_lbl.setText(f"Status: {self.task.status}")
        self.speed_lbl.setText(f"Speed: {human(self.task.speed)}/s")
        self.eta_lbl.setText(f"ETA: {eta_text(self.task.eta)}")
        
        if self.task.sha256:
            self.hash_lbl.setText(self.task.sha256[:32] + "...")
        
        if self.task.status == "Paused":
            self.btn_pause.setText("Resume")
            self.btn_pause.setEnabled(True)
        elif self.task.status in ("Downloading", "Checking...", "Merging"):
            self.btn_pause.setText("Pause")
            self.btn_pause.setEnabled(True)
        else:
            self.btn_pause.setEnabled(False)

    def on_finished(self, _):
        self.update_progress()
        self.btn_pause.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.btn_open.setEnabled(True)
        self.btn_folder.setEnabled(True)
        if self.auto_close_cb.isChecked():
            QTimer.singleShot(1000, self.close)

    def on_failed(self, _, error_msg):
        self.update_progress()
        self.status_lbl.setText("Status: Error")
        self.speed_lbl.setText("Failed")
        self.eta_lbl.setText("")
        self.btn_pause.setEnabled(False)
        self.btn_cancel.setEnabled(False)

class MiniIDM(QMainWindow):
    def __init__(self, start_hidden=False):
        super().__init__()
        self.start_hidden = bool(start_hidden)
        self._startup_background = bool(start_hidden)
        self.setWindowTitle(f"Fast File Downloader — DownGo {CURRENT_VERSION}")
        self.resize(1180, 720)
        self.setMinimumSize(900, 550)
        self.setWindowIcon(make_icon())

        self.tasks = {}
        self.popups = {}
        self._closing = False
        self._anim_offset = 0.0
        self.current_theme = "Dark Mode"
        self.emoji_symbols = ["🚀", "⚡", "🔥", "📥", "👑"]
        self.emoji_idx = 0
        self.custom_bg_path = ""
        self._bg_pixmap = None
        self._sidebar_expanded = True
        self._last_clipboard = ""
        self.scheduled_time = None
        self.auto_shutdown = False
        self.lite_mode = False
        
        self.bridge_signals = BridgeSignals()
        self.bridge_signals.request.connect(self._accept_bridge_request)
        self.tray = QSystemTrayIcon(make_icon(), self)

        self._build_tray()
        self._build_ui()
        self.update_pro_status_ui()
        self._load_ui_prefs()
        self._apply_lite_mode()

        try:
            self.bridge = BridgeServer(self._bridge_request)
            self.bridge.start()
            self.bridge_state = "● BRIDGE ONLINE :127.0.0.1:8765"
        except Exception as e:
            self.bridge = None
            self.bridge_state = f"● BRIDGE ERROR: {e}"

        self._restore()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(300)

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._animate_progress_bars)
        self.anim_timer.start(80)

        self.clip_timer = QTimer(self)
        self.clip_timer.timeout.connect(self._check_clipboard)
        self.clip_timer.start(1000)


        self._check_for_updates()

    def update_pro_status_ui(self):
        self.title_label.setText(f"DownGo  │  {CURRENT_VERSION} FREE")
        if hasattr(self, "btn_pro"):
            self.btn_pro.hide()
        for name in ("btn_speedtest", "theme_combo", "btn_custom_bg", "btn_custom_color", "engine_mode_combo", "auto_extract_cb", "antivirus_cb", "btn_reset_bg"):
            w = getattr(self, name, None)
            if w is not None:
                w.setEnabled(True)
                w.setGraphicsEffect(None)

    def _on_engine_mode_changed(self, index):
        return

    def _on_auto_extract_toggled(self, checked):
        return

    def _on_antivirus_toggled(self, checked):
        return

    def _set_pro_locked(self, widgets, locked):
        for w in widgets:
            if w is not None:
                w.setEnabled(True)
                w.setGraphicsEffect(None)
                w.setToolTip("")

    def on_threads_changed(self, val):
        if self.lite_mode and val > 2:
            self.threads.blockSignals(True)
            self.threads.setValue(2)
            self.threads.blockSignals(False)

    def _check_for_updates(self):
        if STORE_BUILD:
            return
        self.update_thread = UpdateCheckThread()
        self.update_thread.update_available.connect(self._on_update_available)
        self.update_thread.start()

    def _on_update_available(self, latest_ver, download_url, notes):
        msg = (
            f"A new version of DownGo is available!\n\n"
            f"Current Version: {CURRENT_VERSION}\n"
            f"Latest Version: {latest_ver}\n\n"
            f"Release Notes:\n{notes[:300]}...\n\n"
            f"Would you like to download and install the update now?"
        )
        reply = QMessageBox.question(
            self, 
            "Update Available — DownGo", 
            msg, 
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self._download_and_install_update(download_url)

    def _download_and_install_update(self, download_url):
        progress_dialog = QProgressDialog("Downloading update installer...", "Cancel", 0, 100, self)
        progress_dialog.setWindowTitle("Updating DownGo")
        progress_dialog.setModal(True)
        progress_dialog.show()

        self.dl_thread = InstallerDownloadThread(download_url)
        self.dl_thread.progress.connect(progress_dialog.setValue)
        
        def on_finished(installer_path):
            progress_dialog.close()
            QMessageBox.information(
                self, 
                "Update Ready", 
                "Download complete. DownGo will now close to run the installer."
            )
            launch_installer_and_exit(installer_path, self)

        def on_failed(err_msg):
            progress_dialog.close()
            QMessageBox.critical(self, "Update Error", f"Failed to download update: {err_msg}")

        self.dl_thread.finished.connect(on_finished)
        self.dl_thread.failed.connect(on_failed)
        self.dl_thread.start()

    def _build_tray(self):
        menu = QMenu()

        show = QAction("Open DownGo", self)
        show.triggered.connect(self.show_normal)

        add = QAction("Add URL", self)
        add.triggered.connect(self.focus_url)

        speedtest_act = QAction("⚡ Speed Test", self)
        speedtest_act.triggered.connect(self.open_speedtest_modal)

        health = QAction("Bridge: 127.0.0.1:8765", self)
        health.setEnabled(False)

        quit_ = QAction("Exit", self)
        quit_.triggered.connect(self.exit_app)

        menu.addAction(show)
        menu.addAction(add)
        menu.addAction(speedtest_act)
        menu.addSeparator()
        menu.addAction(health)
        menu.addSeparator()
        menu.addAction(quit_)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_click)
        self.tray.setToolTip("DownGo — background download manager")
        self.tray.show()

    def _tray_click(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_normal()

    def _build_ui(self):
        self.setStyleSheet(THEMES["Dark Mode"] + "\nQPushButton#lite { background: #16324a; border: 1px solid #38bdf8; color: #7dd3fc; }\nQPushButton#lite:checked { background: #0f766e; border-color: #5eead4; color: #ccfbf1; }")

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 12, 14, 12)

        top = QHBoxLayout()
        self.title_label = QLabel(f"DownGo  │  {CURRENT_VERSION} FREE")
        self.title_label.setObjectName("title")
        top.addWidget(self.title_label)
        
        self.btn_speedtest = QPushButton("⚡ SPEED TEST")
        self.btn_speedtest.setObjectName("speedtest")
        self.btn_speedtest.clicked.connect(self.open_speedtest_modal)
        top.addWidget(self.btn_speedtest)

        self.btn_lite = QPushButton("🪶 LITE MODE")
        self.btn_lite.setObjectName("lite")
        self.btn_lite.setCheckable(True)
        self.btn_lite.setToolTip("Low-resource mode for PCs with 1–2 GB RAM or weak CPUs")
        self.btn_lite.clicked.connect(self.toggle_lite_mode)
        top.addWidget(self.btn_lite)



        # Custom Theme Combo Box
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        top.addWidget(self.theme_combo)

        self.btn_custom_bg = QPushButton("🖼️ Background")
        self.btn_custom_bg.clicked.connect(self.choose_custom_bg)
        top.addWidget(self.btn_custom_bg)

        self.btn_reset_bg = QPushButton("↺ Default")
        self.btn_reset_bg.setToolTip("Reset to the default theme background")
        self.btn_reset_bg.clicked.connect(self.reset_custom_bg)
        top.addWidget(self.btn_reset_bg)

        self.btn_custom_color = QPushButton("🎨 Color")
        self.btn_custom_color.clicked.connect(self.choose_custom_color)
        top.addWidget(self.btn_custom_color)
        
        top.addStretch()
        self.status = QLabel("● STARTING")
        self.status.setObjectName("muted")
        top.addWidget(self.status)
        root.addLayout(top)

        row = QHBoxLayout()
        self.url = QLineEdit()
        self.url.setPlaceholderText("Enter HTTP/HTTPS URL...")
        self.folder = QLineEdit(str(Path.home() / "Downloads"))
        browse = QPushButton("Folder")
        browse.clicked.connect(self.browse)
        
        self.threads = QSpinBox()
        self.threads.setRange(1, 4)
        self.threads.setValue(4)
        self.threads.valueChanged.connect(self.on_threads_changed)

        self.speed_limit = QSpinBox()
        self.speed_limit.setRange(0, 100000)
        self.speed_limit.setSuffix(" KB/s")
        self.speed_limit.setSpecialValueText("Unlimited")

        self.engine_mode_combo = QComboBox()
        self.engine_mode_combo.addItems(["⚡ Standard Acceleration"])
        self.engine_mode_combo.setToolTip("Standard HTTP acceleration mode")
        self.engine_mode_combo.currentIndexChanged.connect(self._on_engine_mode_changed)

        add = QPushButton("＋ ADD URL")
        add.setObjectName("add")
        add.clicked.connect(self.add_url)

        btn_batch = QPushButton("📋 BATCH")
        btn_batch.clicked.connect(self.open_batch_modal)

        row.addWidget(self.url, 3)
        row.addWidget(QLabel("Cap:"))
        row.addWidget(self.speed_limit)
        row.addWidget(QLabel("Threads:"))
        row.addWidget(self.threads)
        row.addWidget(self.engine_mode_combo)
        row.addWidget(browse)
        row.addWidget(add)
        row.addWidget(btn_batch)
        root.addLayout(row)

        # UI Improvements: Sidebar Splitter Layout
        splitter = QSplitter(Qt.Horizontal)

        self.sidebar = QListWidget()
        self._sidebar_full_labels = ["All Downloads", "Compressed", "Documents", "Music", "Videos", "Programs"]
        self.sidebar.addItems(self._sidebar_full_labels)
        self.sidebar.setMinimumWidth(46)
        self.sidebar.setMaximumWidth(140)
        self.sidebar.currentTextChanged.connect(self._filter_category)
        splitter.addWidget(self.sidebar)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["FILE", "SIZE", "PROGRESS", "RESUME", "SPEED", "ETA", "STATUS", "ID"])
        self.table.setColumnHidden(7, True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        for c in range(1, 7):
            h.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        
        splitter.addWidget(self.table)
        root.addWidget(splitter, 1)

        # Compact live monitor: always visible, small footprint, useful for Store QA.
        self.monitor = QFrame()
        self.monitor.setObjectName("downloadMonitor")
        self.monitor.setStyleSheet("""
            QFrame#downloadMonitor { background: rgba(22,27,34,0.92); border: 1px solid #30363d; border-radius: 10px; }
            QLabel { color: #c9d1d9; }
            QLabel#monitorTitle { color: #58a6ff; font-weight: 700; }
            QLabel#monitorFile { color: #f0f6fc; font-weight: 600; }
            QLabel#monitorAccent { color: #00e5ff; font-weight: 700; }
        """)
        mon = QHBoxLayout(self.monitor)
        mon.setContentsMargins(10, 6, 10, 6)
        mon.setSpacing(10)
        mon.addWidget(QLabel("📡 LIVE MONITOR"), 0)
        self.monitor_file = QLabel("Idle — no active download")
        self.monitor_file.setObjectName("monitorFile")
        self.monitor_file.setMinimumWidth(220)
        self.monitor_file.setMaximumWidth(360)
        self.monitor_file.setToolTip("Current active download")
        mon.addWidget(self.monitor_file, 1)
        self.monitor_progress = QLabel("0%")
        self.monitor_speed = QLabel("0 B/s")
        self.monitor_threads = QLabel("Threads: 0")
        self.monitor_accel = QLabel("Acceleration: Idle")
        self.monitor_accel.setObjectName("monitorAccent")
        for w in (self.monitor_progress, self.monitor_speed, self.monitor_threads, self.monitor_accel):
            mon.addWidget(w, 0)
        root.addWidget(self.monitor)

        actions = QHBoxLayout()
        for text, fn in [
            ("▶ START", self.start),
            ("Ⅱ PAUSE", self.pause),
            ("▶ RESUME", self.resume),
            ("■ CANCEL", self.cancel),
            ("× REMOVE", self.remove),
            ("🔄 REFRESH LINK", self.refresh_expired_link)
        ]:
            b = QPushButton(text)
            b.clicked.connect(fn)
            actions.addWidget(b)

        actions.addStretch()
        hide_btn = QPushButton("— MINIMIZE TO TRAY")
        hide_btn.clicked.connect(self.hide_to_tray)
        actions.addWidget(hide_btn)
        root.addLayout(actions)

        info = QHBoxLayout()
        self.metrics = QLabel("Active: 0    Speed: 0 B/s    Completed: 0")
        self.metrics.setObjectName("muted")
        info.addWidget(self.metrics)
        info.addStretch()
        self.auto_extract_cb = QCheckBox("Auto Extract ZIP/RAR")
        self.antivirus_cb = QCheckBox("Scan with Antivirus")
        self.auto_extract_cb.toggled.connect(self._on_auto_extract_toggled)
        self.antivirus_cb.toggled.connect(self._on_antivirus_toggled)
        self.startup = QCheckBox("Start with Windows")
        self.startup.stateChanged.connect(self.set_startup)
        info.addWidget(self.auto_extract_cb)
        info.addWidget(self.antivirus_cb)
        info.addWidget(self.startup)
        root.addLayout(info)

    def _filter_category(self, category):
        for r in range(self.table.rowCount()):
            id_item = self.table.item(r, 7)
            if not id_item:
                continue
            t = self.tasks.get(id_item.text())
            if not t:
                continue

            if category == "All Downloads":
                self.table.setRowHidden(r, False)
            else:
                cat, _ = get_file_type_info(t.filename)
                self.table.setRowHidden(r, cat.strip("[]").lower() != category.lower())

    def change_theme(self, theme_name):
        self.current_theme = theme_name
        if theme_name in THEMES:
            self.setStyleSheet(THEMES[theme_name])
        self.update()
        self._save_ui_prefs()

    def choose_custom_bg(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if file_path:
            self._set_custom_bg(file_path)

    def reset_custom_bg(self):
        """Clears the custom background and falls back to the current theme's default look."""
        self.custom_bg_path = ""
        self._bg_pixmap = None
        self.centralWidget().setStyleSheet("")
        self.btn_reset_bg.setEnabled(False)
        self.update()
        self._save_ui_prefs()

    def _set_custom_bg(self, path, persist=True):
        pm = QPixmap(path)
        if pm.isNull():
            QMessageBox.warning(self, "DownGo", "Could not load that image as a background.")
            return
        self.custom_bg_path = path.replace('\\', '/')
        self._bg_pixmap = pm
        # Let the window paint the picture; keep the central widget's own
        # background out of the way so the frosted-glass panels show it through.
        self.centralWidget().setAttribute(Qt.WA_StyledBackground, True)
        self.centralWidget().setStyleSheet("background: transparent;")
        self.btn_reset_bg.setEnabled(True)
        self.update()
        if persist:
            self._save_ui_prefs()

    def _save_ui_prefs(self):
        save_ui_settings({"theme": self.current_theme, "bg_path": self.custom_bg_path, "lite_mode": self.lite_mode})

    def _load_ui_prefs(self):
        prefs = load_ui_settings()
        theme = prefs.get("theme")
        bg_path = prefs.get("bg_path", "")
        self.lite_mode = bool(prefs.get("lite_mode", False))

        if theme and theme in THEMES:
            self.current_theme = theme
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentText(theme)
            self.theme_combo.blockSignals(False)
            self.setStyleSheet(THEMES[theme])

        if bg_path and os.path.exists(bg_path):
            self._set_custom_bg(bg_path, persist=False)

    # Default backdrop gradients for glass-style themes when the user
    # hasn't picked a custom background image — keeps the frosted panels
    # sitting on something intentional instead of an empty black canvas.
    _GLASS_GRADIENTS = {
        "Aurora Glass": [
            (0.0, QColor(255, 205, 165)),
            (0.35, QColor(255, 154, 198)),
            (0.65, QColor(161, 140, 255)),
            (1.0, QColor(140, 200, 255)),
        ],
        "Glass UI": [
            (0.0, QColor(15, 23, 42)),
            (1.0, QColor(51, 65, 85)),
        ],
        "Frosted Glass": [
            (0.0, QColor(226, 232, 240)),
            (1.0, QColor(255, 255, 255)),
        ],
    }

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        if self._bg_pixmap and not self._bg_pixmap.isNull():
            scaled = self._bg_pixmap.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            # A soft tint keeps the frosted-glass panels readable over any photo.
            tint = QColor(255, 255, 255, 40) if "Glass" in self.current_theme else QColor(10, 10, 18, 90)
            painter.fillRect(self.rect(), tint)
        else:
            stops = self._GLASS_GRADIENTS.get(self.current_theme)
            if stops:
                grad = QLinearGradient(0, 0, self.width(), self.height())
                for pos, color in stops:
                    grad.setColorAt(pos, color)
                painter.fillRect(self.rect(), grad)

        painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_layout(event.size().width())

    def _apply_responsive_layout(self, width):
        """Soft, auto-adjusting layout: the sidebar eases itself narrower on
        smaller windows and back out again, instead of snapping abruptly."""
        compact = width < 980
        expanded = not compact
        if expanded == self._sidebar_expanded:
            return
        self._sidebar_expanded = expanded

        if getattr(self, "lite_mode", False):
            self.sidebar.setMaximumWidth(140 if expanded else 46)
            return
        anim = QPropertyAnimation(self.sidebar, b"maximumWidth", self)
        anim.setDuration(220)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.setStartValue(self.sidebar.maximumWidth())
        anim.setEndValue(140 if expanded else 46)
        anim.start()
        self._sidebar_anim = anim  # keep a reference so it isn't garbage-collected mid-animation

    def toggle_lite_mode(self, checked):
        self.lite_mode = bool(checked)
        self._apply_lite_mode()
        self._save_ui_prefs()

    def _apply_lite_mode(self):
        """Reduce CPU/RAM/background activity for very low-end Windows PCs."""
        if not hasattr(self, "btn_lite"):
            return
        self.btn_lite.blockSignals(True)
        self.btn_lite.setChecked(self.lite_mode)
        self.btn_lite.setText("🪶 LITE ON" if self.lite_mode else "🪶 LITE MODE")
        self.btn_lite.blockSignals(False)
        if self.lite_mode:
            self.btn_lite.setToolTip("Lite mode ON: low CPU/RAM profile — animations disabled, up to 2 download connections")
            if hasattr(self, "timer"): self.timer.setInterval(1000)
            if hasattr(self, "anim_timer"):
                self.anim_timer.stop()
            if hasattr(self, "clip_timer"): self.clip_timer.setInterval(3000)
            if hasattr(self, "schedule_timer"): self.schedule_timer.setInterval(30000)
            # Stop premium/locked visual effects too. Lite means genuinely quiet UI.
            for attr in ("_pro_bubble_anim", "_lite_anim", "_sidebar_anim"):
                anim = getattr(self, attr, None)
                if anim is not None and hasattr(anim, "stop"):
                    anim.stop()
            if hasattr(self, "_set_pro_lock_effects_static"):
                self._set_pro_lock_effects_static()
        else:
            self.btn_lite.setToolTip("Low-resource mode for PCs with 1–2 GB RAM or weak CPUs")
            if hasattr(self, "timer"): self.timer.setInterval(300)
            if hasattr(self, "anim_timer"): self.anim_timer.setInterval(80); self.anim_timer.start()
            if hasattr(self, "clip_timer"): self.clip_timer.setInterval(1000)
            if hasattr(self, "schedule_timer"): self.schedule_timer.setInterval(10000)
        if self.lite_mode:
            # Existing queued tasks are not restarted automatically; new starts use the lite profile.
            self.threads.setValue(min(2, self.threads.value()))
            self.threads.setToolTip("Lite mode: limited to 2 connections to reduce RAM/CPU usage")
        else:
            self.threads.setToolTip("Up to 4 connections in Free edition")

    def _set_pro_lock_effects_static(self):
        """Remove visual opacity animations while Lite Mode is active."""
        for w in getattr(self, "_pro_locked_widgets", []):
            effect = getattr(w, "_pro_lock_effect", None)
            anim = getattr(w, "_pro_lock_anim", None)
            if anim is not None:
                anim.stop()
            if effect is not None:
                effect.setOpacity(0.72)

    def choose_custom_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            custom_style = self.styleSheet() + f"\nQPushButton {{ border-color: {hex_color}; color: {hex_color}; }}"
            self.setStyleSheet(custom_style)

    def open_speedtest_modal(self):
        modal = SpeedTestModal(self)
        modal.exec()

    def open_batch_modal(self):
        modal = BatchImportModal(self)
        if modal.exec() == QDialog.Accepted:
            for u in modal.urls:
                self._create_task(u)

    def _check_clipboard(self):
        cb = QApplication.clipboard().text().strip()
        if cb and cb != self._last_clipboard and cb.startswith(("http://", "https://")):
            if any(cb.endswith(ext) for ext in [".zip", ".exe", ".pdf", ".mp4", ".iso", ".rar"]):
                self._last_clipboard = cb
                ans = QMessageBox.question(
                    self, "DownGo Link Detector",
                    f"Download link detected in clipboard:\n{cb[:60]}...\nAdd to DownGo?"
                )
                if ans == QMessageBox.Yes:
                    self.url.setText(cb)
                    self.add_url()

    def _animate_progress_bars(self):
        self._anim_offset = (self._anim_offset + 0.1) % 1.0
        self.emoji_idx = (self.emoji_idx + 1) % len(self.emoji_symbols)
        current_emoji = self.emoji_symbols[self.emoji_idx]

        stop0 = round(self._anim_offset, 2)
        stop1 = round((self._anim_offset + 0.3) % 1.0, 2)
        
        style = f"""
            QProgressBar {{
                border: 1px solid #21262d; border-radius: 4px; background: #161b22;
                text-align: center; color: #f0f6fc; font-weight: bold; font-size: 11px; height: 16px;
            }}
            QProgressBar::chunk {{
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #008ba3, stop:{stop0} #00bcd4, stop:{stop1} #80f0ff, stop:1 #00e5ff
                );
                border-radius: 3px;
            }}
        """

        pro_active = True

        for r in range(self.table.rowCount()):
            bar = self.table.cellWidget(r, 2)
            if isinstance(bar, QProgressBar):
                bar.setStyleSheet(style)
                val = bar.value()
                if pro_active:
                    if 0 < val < 100:
                        bar.setFormat(f"{current_emoji} %p%")
                    elif val == 100:
                        bar.setFormat("✅ 100%")
                else:
                    bar.setFormat("%p%")

        for popup in self.popups.values():
            if hasattr(popup, "bar"):
                popup.bar.setStyleSheet(style)
                val = popup.bar.value()
                if pro_active:
                    if 0 < val < 100:
                        popup.bar.setFormat(f"{current_emoji} %p%")
                    elif val == 100:
                        popup.bar.setFormat("✅ 100%")
                else:
                    popup.bar.setFormat("%p%")

    def _create_task(self, url, filename_hint="", referrer=""):
        tid = uuid.uuid4().hex[:10]
        connections = min(2, self.threads.value()) if self.lite_mode else (min(4, self.threads.value()))
        t = DownloadTask(
            tid, url, self.folder.text(),
            connections, filename_hint=filename_hint,
            speed_limit_kbps=self.speed_limit.value(), referrer=referrer, lite_mode=self.lite_mode
        )
        t.changed.connect(self.refresh)
        t.finished.connect(self.completed)
        t.failed.connect(self.failed)

        self.tasks[tid] = t
        self._add_row(t)
        
        # One authoritative probe only. This avoids duplicate requests and UI
        # race conditions during Store certification testing.
        t.start()
        self.save()
        return t

    def _check_resume_async(self, t):
        can_resume = check_resume_capability(t.url)
        t.can_resume = can_resume
        self.refresh()

    def add_url(self):
        url = self.url.text().strip()
        try:
            validate_url(url)
        except ValueError as e:
            QMessageBox.warning(self, "DownGo — Invalid URL", str(e))
            return
        try:
            self._create_task(url)
            self.url.clear()
        except Exception as e:
            QMessageBox.critical(self, "DownGo — Could not add URL", str(e))

    def refresh_expired_link(self):
        t = self.selected()
        if not t:
            QMessageBox.warning(self, "Warning", "Please select a download task to refresh.")
            return

        new_url, ok = QInputDialog.getText(self, "Refresh Link / Address", "Enter new download URL:")
        if ok and new_url.startswith(("http://", "https://")):
            t.url = new_url.strip()
            QMessageBox.information(self, "Success", "Download URL successfully updated! You can now Resume.")
            self.save()

    def _bridge_request(self, request):
        self.bridge_signals.request.emit(request)

    def _accept_bridge_request(self, request):
        try:
            url = request["url"]
            filename = request.get("filename", "")
            if not url.startswith(("http://", "https://")):
                request["result"].put_nowait({"accepted": False, "error": "Unsupported URL"})
                return

            t = self._create_task(url, filename, request.get("referrer", ""))
            self.show_download_popup(t)
            request["result"].put_nowait({
                "accepted": True,
                "task_id": t.id,
                "filename": t.filename
            })
        except Exception as e:
            try:
                request["result"].put_nowait({"accepted": False, "error": str(e)})
            except queue.Full:
                pass

    def show_download_popup(self, task):
        if task.id in self.popups:
            self.popups[task.id].showNormal()
            self.popups[task.id].raise_()
            self.popups[task.id].activateWindow()
            return
        popup = DownloadProgressWindow(task, parent=self)
        self.popups[task.id] = popup
        popup.show()
        popup.raise_()
        popup.activateWindow()

    def _add_row(self, t):
        r = self.table.rowCount()
        self.table.insertRow(r)
        
        type_str, _ = get_file_type_info(t.filename)
        display_name = f"{type_str}  {t.filename}"

        vals = [display_name, "0 B", "", "🔍 Check...", "0 B/s", "--:--", t.status, t.id]
        for c, v in enumerate(vals):
            if c == 2:
                bar = QProgressBar()
                bar.setRange(0, 100)
                bar.setValue(0)
                bar.setTextVisible(True)
                self.table.setCellWidget(r, 2, bar)
            else:
                self.table.setItem(r, c, QTableWidgetItem(str(v)))

    def selected(self):
        r = self.table.currentRow()
        if r < 0:
            return None
        item = self.table.item(r, 7)
        if not item:
            return None
        return self.tasks.get(item.text())

    def start(self):
        t = self.selected()
        if t:
            t.start()

    def pause(self):
        t = self.selected()
        if t:
            t.pause()

    def resume(self):
        t = self.selected()
        if t:
            t.resume()

    def cancel(self):
        t = self.selected()
        if t:
            t.cancel()

    def remove(self):
        t = self.selected()
        if not t:
            return
        if t.status in ("Downloading", "Checking...", "Merging"):
            t.cancel()
        r = self.table.currentRow()
        self.table.removeRow(r)
        self.tasks.pop(t.id, None)
        self.save()

    def completed(self, t):
        self.refresh()
        self.save()

        if True:
            # Antivirus scanning is performed exactly once by DownloadTask before
            # this completion signal. Never launch a second Defender scan here.
            if self.auto_extract_cb.isChecked() and t.path.lower().endswith(".zip"):
                # Extraction is allowed only after a clean Defender result.
                if getattr(t, "scan_status", "not_requested") == "clean":
                    try:
                        extract_path = os.path.splitext(t.path)[0]
                        safe_root = os.path.realpath(extract_path)
                        os.makedirs(extract_path, exist_ok=True)
                        with zipfile.ZipFile(t.path, "r") as zip_ref:
                            for member in zip_ref.infolist():
                                member_path = os.path.realpath(os.path.join(extract_path, member.filename))
                                if not (member_path == safe_root or member_path.startswith(safe_root + os.sep)):
                                    raise RuntimeError("Unsafe archive path blocked during extraction.")
                            zip_ref.extractall(extract_path)
                    except Exception as exc:
                        self.tray.showMessage("DownGo — Extraction blocked", str(exc), QSystemTrayIcon.Warning, 5000)
                else:
                    self.tray.showMessage("DownGo — Security check", "ZIP was not auto-extracted because antivirus verification was not confirmed clean.", QSystemTrayIcon.Warning, 5000)

        self.tray.showMessage(
            "DownGo Download Complete",
            f"File saved to: {t.filename}\nSHA-256: {t.sha256[:12]}...",
            QSystemTrayIcon.Information,
            5000
        )

        if self.auto_shutdown:
            active_count = sum(1 for task in self.tasks.values() if task.status in ("Downloading", "Checking..."))
            if active_count == 0:
                subprocess.Popen(["shutdown.exe", "/s", "/t", "60"])

    def failed(self, t, msg):
        self.tray.showMessage(
            "DownGo — Download Error",
            f"{t.filename}\n{msg}",
            QSystemTrayIcon.Critical,
            6000
        )
        self.save()

    def refresh(self):
        active = 0
        speed = 0
        done = 0

        for r in range(self.table.rowCount()):
            id_item = self.table.item(r, 7)
            if not id_item:
                continue
            tid = id_item.text()
            t = self.tasks.get(tid)
            if not t:
                continue

            if t.status in ("Downloading", "Checking...", "Merging"):
                active += 1
            if t.status == "Completed":
                done += 1

            speed += t.speed or 0
            pct = (t.downloaded / t.total * 100) if t.total else 0

            type_str, _ = get_file_type_info(t.filename)
            
            for col in (0, 1, 3, 4, 5, 6):
                if not self.table.item(r, col):
                    self.table.setItem(r, col, QTableWidgetItem(""))

            self.table.item(r, 0).setText(f"{type_str}  {t.filename}")
            self.table.item(r, 1).setText(f"{human(t.downloaded)} / {human(t.total)}")
            
            bar = self.table.cellWidget(r, 2)
            if isinstance(bar, QProgressBar):
                bar.setValue(int(pct))
                
            resume = getattr(t, "can_resume", None)
            if resume is None and t.status in ("Queued", "Checking..."):
                resume_str = "🔍 Checking..."
            else:
                resume_str = "🟢 Yes" if bool(resume) else "🔴 No"
            self.table.item(r, 3).setText(resume_str)

            self.table.item(r, 4).setText(human(t.speed) + "/s")
            self.table.item(r, 5).setText(eta_text(t.eta))
            self.table.item(r, 6).setText(t.status)
            if t.status == "Error" and getattr(t, "error", ""):
                self.table.item(r, 6).setToolTip(t.error)
            else:
                self.table.item(r, 6).setToolTip("")

        self.metrics.setText(
            f"Active: {active}    Speed: {human(speed)}/s    Completed: {done}"
        )

        active_tasks = [t for t in self.tasks.values() if t.status in ("Downloading", "Checking...", "Merging")]
        if active_tasks:
            mt = max(active_tasks, key=lambda x: x.speed or 0)
            mpct = (mt.downloaded / mt.total * 100) if mt.total else 0
            self.monitor_file.setText(mt.filename)
            self.monitor_file.setToolTip(mt.path)
            self.monitor_progress.setText(f"{mpct:.0f}%")
            self.monitor_speed.setText(f"{human(mt.speed)}/s")
            self.monitor_threads.setText(f"Threads: {mt.connections}/{mt.requested_connections}")
            self.monitor_accel.setText(f"Acceleration: {mt.connections}-thread {getattr(mt, 'acceleration_mode', 'active')}")
        else:
            self.monitor_file.setText("Idle — no active download")
            self.monitor_file.setToolTip("")
            self.monitor_progress.setText("0%")
            self.monitor_speed.setText("0 B/s")
            self.monitor_threads.setText("Threads: 0")
            self.monitor_accel.setText("Acceleration: Idle")

        bridge = getattr(self, "bridge_state", "● BRIDGE STARTING")
        self.status.setText(bridge if active == 0 else "● DOWNLOAD ENGINE ACTIVE")

    def browse(self):
        p = QFileDialog.getExistingDirectory(self, "Download folder", self.folder.text())
        if p:
            self.folder.setText(p)

    def focus_url(self):
        self.show_normal()
        self.url.setFocus()

    def hide_to_tray(self):
        self.hide()
        self.tray.showMessage(
            "DownGo",
            "Running in background. Downloads will continue.",
            QSystemTrayIcon.Information,
            3000
        )

    def show_normal(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        if self._closing:
            event.accept()
            return
        event.ignore()
        self.hide_to_tray()

    def exit_app(self):
        self._closing = True
        
        # 1. Stop all Timers
        self.timer.stop()
        self.anim_timer.stop()
        self.clip_timer.stop()
        self.schedule_timer.stop()

        # 2. Close Popup Dialogs
        for popup in list(self.popups.values()):
            popup.close()

        # 3. Cancel Active Tasks
        for t in self.tasks.values():
            if t.status in ("Downloading", "Checking...", "Merging"):
                t.cancel()

        # 4. Stop Bridge Server
        if self.bridge:
            self.bridge.stop()

        # 5. Save Queue
        self.save()

        # 6. Hide System Tray
        self.tray.hide()

        # 7. Quit Application Cleanly
        QApplication.quit()

    def save(self):
        data = []
        for t in self.tasks.values():
            data.append({
                "id": t.id,
                "url": t.url,
                "folder": t.base_folder,
                "connections": t.connections,
                "filename": t.filename,
                "path": t.path,
                "status": t.status,
                "downloaded": t.downloaded,
                "total": t.total,
                "sha256": t.sha256
            })
        try:
            HISTORY.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _restore(self):
        if not HISTORY.exists():
            return
        try:
            data = json.loads(HISTORY.read_text(encoding="utf-8"))
            for d in data:
                if d.get("status") == "Completed":
                    continue

                t = DownloadTask(
                    d["id"], d["url"], d.get("folder", str(Path.home() / "Downloads")),
                    min(2, max(1, int(d.get("connections", 2)))) if self.lite_mode else min(4, max(1, int(d.get("connections", 4)))), filename_hint=d.get("filename", ""), lite_mode=self.lite_mode
                )
                t.path = d.get("path", t.path)
                t.downloaded = d.get("downloaded", 0)
                t.total = d.get("total", 0)
                t.sha256 = d.get("sha256", "")
                status = d.get("status", "Queued")
                if status in ("Downloading", "Checking...", "Merging"):
                    status = "Paused"
                t.status = status
                t.changed.connect(self.refresh)
                t.finished.connect(self.completed)
                t.failed.connect(self.failed)
                self.tasks[t.id] = t
                self._add_row(t)
        except Exception:
            pass

    def set_startup(self, state):
        if os.name != "nt":
            return

        startup = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Startup"
        bat = startup / "DownGo-Background.bat"

        if state:
            exe = sys.executable
            entry = Path(__file__).resolve().parent / "main.py"
            bat.write_text(
                f'@echo off\nstart "" "{exe}" "{entry}" --background\n',
                encoding="utf-8"
            )
        else:
            try:
                bat.unlink()
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MiniIDM(start_hidden=("--background" in sys.argv))
    if "--background" not in sys.argv:
        window.show()
    sys.exit(app.exec())
