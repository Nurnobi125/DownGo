# DownGo Free (v3.2)

A fast, lightweight open-source Windows download manager built with Python and PySide6, featuring an IDM-style desktop UI and local browser integration.

---

## Features

- **IDM-Style Desktop UI:** Clean, modern interface designed for ease of use.
- **System Tray / Background Mode:** Runs quietly in the system tray so your downloads continue uninterrupted.
- **Multi-Connection Downloads:** Supports concurrent connections for faster HTTP/HTTPS downloads.
- **Full Control:** Pause, resume, and cancel downloads anytime.
- **Real-Time Analytics:** Live tracking of download speed, progress percentage, and estimated time of arrival (ETA).
- **Download History:** Automatically saves and restores your queue across sessions.
- **Windows Startup Option:** Option to launch DownGo automatically with Windows.
- **Local Browser Bridge:** Local server running on `127.0.0.1:8765` for seamless browser communication.
- **Chrome/Edge Manifest V3 Support:** Intercepts browser downloads and routes them directly to DownGo.
- **Smart Filename Detection:** Accurately detects filenames using `Content-Disposition` headers and URL parsing.

---

## Requirements

- Python 3.10 or higher
- Windows 10/11

---

## Getting Started & Running Locally

1. Clone or download this repository.
2. Install the required dependencies:
   ```bat
   python -m pip install -r requirements.txt
