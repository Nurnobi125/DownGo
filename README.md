# DownGo Free (v3.2)

A fast, lightweight open-source Windows download manager built with Python and PySide6, featuring an IDM-style desktop UI and local browser integration.

---

<p align="center">
  <img src="icon.ico" width="120" height="120" alt="DownGo Logo">
</p>

<h1 align="center">DownGo v3.2</h1>

<p align="center">
  <b>A fast, lightweight Windows download manager built with Python and PySide6, featuring an IDM-style desktop UI and seamless browser integration.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python" alt="Python Version">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%2F11-lightgrey?style=flat-square&logo=windows" alt="Windows">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="MIT License">
</p>

---

## 📸 Interface Preview

<p align="center">
  <img src="Screenshot (717).png" alt="DownGo UI Screenshot" width="100%">
</p>

---

## ✨ Features

- **IDM-Style Desktop UI:** Clean, modern, dark-themed user interface designed for high performance and ease of use.
- **System Tray / Background Mode:** Runs quietly in the system tray so your downloads continue uninterrupted.
- **Multi-Connection Downloads:** Supports concurrent threads/connections to maximize download speeds.
- **Full Control:** Pause, resume, cancel, and refresh expired download links effortlessly.
- **Real-Time Analytics:** Live tracking of download speed, exact progress percentage, and estimated time of arrival (ETA).
- **Download History & Queue:** Automatically saves and restores your active queue across sessions.
- **Windows Startup Option:** Built-in option to launch DownGo automatically with Windows.
- **Local Browser Bridge:** Local background server running on `127.0.0.1:8765` for lightning-fast browser communication.
- **Chrome/Edge Manifest V3 Support:** Intercepts browser downloads and routes them directly into DownGo.
- **Smart Filename Detection:** Accurately detects filenames using `Content-Disposition` headers and URL parsing.

---

## 🛠️ Requirements

- Python 3.10 or higher
- Windows 10/11

---

## 🚀 Getting Started & Running Locally

1. Clone or download this repository.
2. Install the required dependencies:
   ```bat
   python -m pip install -r requirements.txt
