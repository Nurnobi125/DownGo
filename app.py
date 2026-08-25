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

from PySide6.QtCore import Qt, QTimer, QObject, Signal, QTime, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor, QLinearGradient, QFont, QClipboard
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QFileDialog, QSpinBox, QLabel, QFrame,
    QSystemTrayIcon, QMenu, QMessageBox, QHeaderView, QDialog,
    QAbstractItemView, QCheckBox, QProgressBar, QRadioButton, QButtonGroup, QTextEdit,
    QProgressDialog, QInputDialog, QComboBox, QColorDialog, QListWidget, QTimeEdit, QSplitter,
    QGraphicsOpacityEffect
)

from downloader import DownloadTask, get_file_type_info
from speedtest import SpeedTestEngine
from bridge import BridgeServer
from updater import UpdateCheckThread, InstallerDownloadThread, launch_installer_and_exit, CURRENT_VERSION

APP_DIR = Path.home() / ".mini_idm"
APP_DIR.mkdir(exist_ok=True)
HISTORY = APP_DIR / "queue.json"
UI_SETTINGS_FILE = APP_DIR / "ui_settings.json"

# --- Free Themes (Standard) ---
THEMES = {
    "Dark Mode": """
        QMainWindow, QWidget { background: #0d1117; color: #c9d1d9; font-family: 'Segoe UI', Arial; }
        QLineEdit, QSpinBox, QTextEdit, QComboBox, QTimeEdit { background: #161b22; border: 1px solid #30363d; color: #f0f6fc; padding: 6px; border-radius: 6px; }
        QPushButton { background: #21262d; border: 1px solid #30363d; color: #c9d1d9; padding: 6px 14px; border-radius: 6px; font-weight: 600; }
        QPushButton:hover { background: #30363d; border-color: #8b949e; color: #ffffff; }
        QPushButton#add { background: #238636; border-color: #2ea043; color: #ffffff; }
        QPushButton#add:hover { background: #2ea043; }
        QTableWidget { background: #0d1117; border: 1px solid #21262d; gridline-color: transparent; color: #c9d1d9; font-family: 'Consolas', 'Fira Code', monospace; font-size: 12px; }
        QTableWidget::item { padding: 6px; border-bottom: 1px solid #161b22; }
        QTableWidget::item:selected { background-color: #1f242c; color: #58a6ff; }
        QListWidget { background: #161b22; border: 1px solid #21262d; color: #c9d1d9; border-radius: 6px; }
        QListWidget::item { padding: 8px; border-radius: 4px; }
        QListWidget::item:selected { background: #1f6beb; color: #ffffff; font-weight: bold; }
        QHeaderView::section { background: #161b22; color: #8b949e; border: none; border-bottom: 1px solid #30363d; padding: 6px; font-weight: 600; }
        QLabel#title { color: #58a6ff; font-size: 16px; font-weight: bold; }
        QLabel#muted { color: #8b949e; }
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

def check_resume_capability(url):
    try:
        r = requests.head(url, allow_redirects=True, timeout=5)
        headers = r.headers
        if 'Accept-Ranges' in headers and headers['Accept-Ranges'] == 'bytes':
            return True
        if 'content-range' in headers:
            return True
        return False
    except Exception:
        return False

class BatchImportModal(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Link Importer — DownGo Free")
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
                subprocess.Popen(f'explorer /select,"{os.path.abspath(self.task.path)}"')
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
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Fast File Downloader — DownGo Free {CURRENT_VERSION}")
        self.resize(1180, 720)
        self.setMinimumSize(900, 550)
        self.setWindowIcon(make_icon())

        self.tasks = {}
        self.popups = {}
        self._closing = False
        self._sidebar_expanded = True
        self._last_clipboard = ""
        
        self.bridge_signals = BridgeSignals()
        self.bridge_signals.request.connect(self._accept_bridge_request)
        self.tray = QSystemTrayIcon(make_icon(), self)

        self._build_tray()
        self._build_ui()

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

        self.clip_timer = QTimer(self)
        self.clip_timer.timeout.connect(self._check_clipboard)
        self.clip_timer.start(1000)

        self._check_for_updates()

    def on_threads_changed(self, val):
        # Free version max threads limited to 4 safely
        if val > 4:
            self.threads.setValue(4)

    def _check_for_updates(self):
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

        health = QAction("Bridge: 127.0.0.1:8765", self)
        health.setEnabled(False)

        quit_ = QAction("Exit", self)
        quit_.triggered.connect(self.exit_app)

        menu.addAction(show)
        menu.addAction(add)
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
        self.setStyleSheet(THEMES["Dark Mode"])

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 12, 14, 12)

        top = QHBoxLayout()
        self.title_label = QLabel(f"DownGo FREE  │  {CURRENT_VERSION}")
        self.title_label.setObjectName("title")
        top.addWidget(self.title_label)
        
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
        self.threads.setRange(1, 4)  # Free version restricted to 4 threads
        self.threads.setValue(2)
        self.threads.valueChanged.connect(self.on_threads_changed)

        self.speed_limit = QSpinBox()
        self.speed_limit.setRange(0, 100000)
        self.speed_limit.setSuffix(" KB/s")
        self.speed_limit.setSpecialValueText("Unlimited")

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
        row.addWidget(browse)
        row.addWidget(add)
        row.addWidget(btn_batch)
        root.addLayout(row)

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
        
        self.startup = QCheckBox("Start with Windows")
        self.startup.stateChanged.connect(self.set_startup)
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

    def _create_task(self, url, filename_hint=""):
        tid = uuid.uuid4().hex[:10]
        t = DownloadTask(
            tid, url, self.folder.text(),
            self.threads.value(), filename_hint=filename_hint,
            speed_limit_kbps=self.speed_limit.value()
        )
        t.changed.connect(self.refresh)
        t.finished.connect(self.completed)
        t.failed.connect(self.failed)

        self.tasks[tid] = t
        self._add_row(t)
        
        threading.Thread(target=self._check_resume_async, args=(t,), daemon=True).start()

        t.start()
        self.save()
        return t

    def _check_resume_async(self, t):
        can_resume = check_resume_capability(t.url)
        t.can_resume = can_resume
        self.refresh()

    def add_url(self):
        url = self.url.text().strip()
        if not url.startswith(("http://", "https://")):
            QMessageBox.warning(self, "DownGo", "Please enter a valid HTTP/HTTPS URL.")
            return
        self._create_task(url)
        self.url.clear()

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

            t = self._create_task(url, filename)
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
        self.tray.showMessage(
            "DownGo Download Complete",
            f"File saved to: {t.filename}\nSHA-256: {t.sha256[:12]}...",
            QSystemTrayIcon.Information,
            5000
        )

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
                
            resume_str = "🟢 Yes" if getattr(t, 'can_resume', False) else "🔴 No"
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
        self.timer.stop()
        self.clip_timer.stop()

        for popup in list(self.popups.values()):
            popup.close()

        for t in self.tasks.values():
            if t.status in ("Downloading", "Checking...", "Merging"):
                t.cancel()

        if self.bridge:
            self.bridge.stop()

        self.save()
        self.tray.hide()
        QApplication.quit()
        os._exit(0)

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
                    d.get("connections", 2), filename_hint=d.get("filename", "")
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
        bat = startup / "Mini-IDM-Background.bat"

        if state:
            exe = sys.executable
            script = Path(__file__).resolve().parent / "app.py"
            bat.write_text(
                f'@echo off\nstart "" "{exe}" "{script}"\n',
                encoding="utf-8"
            )
        else:
            try:
                bat.unlink()
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MiniIDM()
    window.show()
    sys.exit(app.exec())