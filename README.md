# DownGo — Fast & Lightweight Windows Download Manager

<p align="center">
  <img src="icon.ico" width="120" height="120" alt="DownGo Logo">
</p>

<h1 align="center">DownGo 4.0.7</h1>

<p align="center">
  <b>A fast, reliable and lightweight Windows download manager with multi-thread acceleration, pause & resume, browser integration, security scanning, speed testing and Lite Mode.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-4.0.7-blue?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/PySide6-6.x-green?style=flat-square" alt="PySide6">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%2F11-lightgrey?style=flat-square&logo=windows" alt="Windows">
  <img src="https://img.shields.io/badge/Status-Active%20Development-success?style=flat-square" alt="Status">
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#lite-mode">Lite Mode</a> •
  <a href="#security">Security</a> •
  <a href="#testing">Testing</a> •
  <a href="#contributing">Contributing</a>
</p>

---

## 📖 About

**DownGo** is a modern Windows download manager built with **Python and PySide6**.

It is designed to provide fast downloads without sacrificing reliability or system performance.

DownGo supports multi-connection acceleration when the server supports HTTP Range requests, while automatically falling back to a normal single-connection download when necessary.

The application also includes pause/resume, automatic retry, browser integration, download history, system-tray operation, a built-in speed tester, security scanning and a dedicated Lite Mode for low-end PCs.

---

## ✨ Features

### ⚡ Fast Multi-Connection Downloads

- Multi-thread download acceleration
- HTTP Range request support
- Automatic `206 Partial Content` validation
- Automatic single-connection fallback
- Configurable connection count
- Real-time download speed
- Thread/connection monitoring
- Large-file support

### 📡 Live Download Monitor

Monitor active downloads directly from the application.

Shows:

- Current file
- Download percentage
- Current speed
- ETA
- Active threads
- Connection mode
- Download status

Example:

```text
📡 LIVE DOWNLOAD MONITOR

Ubuntu.iso
████████████████░░░░  78%

Speed:       8.4 MB/s
Threads:     16 / 16
Mode:        Multi-Range
Status:      Downloading
