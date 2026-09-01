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
Example:

```text
📡 LIVE DOWNLOAD MONITOR

Ubuntu.iso
████████████████░░░░  78%

Speed:       8.4 MB/s

Threads:     16 / 16
Mode:        Multi-Range
Status:      Downloading

Monitor active downloads directly from the application.

Shows:

- Current file
- Download percentage
- Current speed
- ETA
- Active threads
- Connection mode
- Download status
⏯️ Pause & Resume

DownGo is designed for unstable internet connections.

Pause downloads
Resume downloads
Resume after application restart
Retry failed connections
Recover interrupted downloads
Handle expired/failed connections
Automatic retry with backoff
🔄 Smart Error & Retry Engine

DownGo handles common temporary network failures without unnecessarily restarting the entire download.

Supported recovery scenarios include:

Connection timeout
Network interruption
HTTP 408
HTTP 429
HTTP 500
HTTP 502
HTTP 503
HTTP 504
Redirects
Unsupported Range servers
🪶 Lite Mode

DownGo includes a dedicated Lite Mode for low-end Windows PCs.

Lite Mode is available to both Free and Pro users.

Designed for
1 GB–4 GB RAM systems
Older Intel/AMD processors
Older laptops
Low-power PCs
Systems running multiple applications
Lite Mode optimizations
Reduces background polling
Reduces UI refresh frequency
Disables non-essential animations
Reduces HTTP connection pool size
Limits download connections
Reduces unnecessary CPU activity
Minimizes visual effects
Normal Mode
    ↓
Full UI + animations
    ↓
Higher responsiveness

Lite Mode
    ↓
Reduced animations
    ↓
Reduced background activity
    ↓
Lower CPU/RAM overhead

Lite Mode does not disable core download functionality.

🌐 Browser Integration

DownGo includes a local browser bridge for desktop browser integration.

Chrome / Edge
      ↓
Browser Extension
      ↓
127.0.0.1:8765
      ↓
DownGo
      ↓
Download Manager

Features:

Chrome support
Microsoft Edge support
Manifest V3 browser extension
Local browser communication
Automatic download interception
Direct URL handoff to DownGo
📁 File Support

DownGo is designed to handle common downloadable file types:

Documents
PDF
TXT
CSV
DOC/DOCX
XLS/XLSX
PPT/PPTX
Images
JPG/JPEG
PNG
GIF
WEBP
SVG
Audio
MP3
WAV
FLAC
OGG
M4A
Video
MP4
MKV
WEBM
MOV
AVI
Archives
ZIP
7Z
TAR
GZ
📦 Automatic ZIP Extraction

Supported ZIP downloads can be automatically extracted after security validation.

Features:

Automatic ZIP detection
Automatic destination folder
Safe extraction
Path traversal protection
Corrupt archive handling
Antivirus-before-extraction workflow

DownGo does not automatically execute files extracted from downloads.

🛡️ Security

Security is an important part of the download workflow.

For supported Windows systems, DownGo can use Microsoft Defender to scan downloaded files.

Security workflow:

Download
   ↓
SHA-256 verification
   ↓
Microsoft Defender scan
   ↓
Clean?
 ┌───────┴───────┐
 YES             NO
 ↓                ↓
Extract          Block
 ↓                ↓
Complete         Warning

DownGo does not intentionally auto-run downloaded executable files.

ZIP extraction also validates paths to help prevent path traversal attacks.

Antivirus availability and scan behavior depend on the Windows security configuration.

📊 Built-in Internet Speed Test

DownGo includes a built-in network speed tester.

It can measure:

Latency / ping
Download throughput
Upload throughput
Connection status
Test progress

The test runs without blocking the main application interface.

🗂️ Download Queue & History

DownGo maintains download state across sessions.

Features include:

Download queue
Active downloads
Completed downloads
Failed downloads
Download history
Resume support
Persistent task state
File categorization
🖥️ System Tray & Background Mode

DownGo can run in the Windows system tray.

When configured for Windows startup:

Windows starts
      ↓
DownGo starts
      ↓
Background mode
      ↓
System Tray
      ↓
Main window remains closed

The main window can be opened manually from the tray.

This prevents unnecessary UI popups during Windows startup.

💧 Pro Edition

DownGo Pro provides additional features for advanced users.

Possible Pro features include:

Higher connection limits
Advanced acceleration
Advanced download controls
Premium interface features
Automatic extraction
Advanced security workflow
Scheduling
Additional monitoring features

Pro activation is handled through the application's licensing system.

🧠 Smart Download Strategy

DownGo does not blindly use maximum threads for every server.

The engine first checks server capabilities.

Download URL
     ↓
Server Detection
     ↓
Range Supported?
   ↙       ↘
 YES       NO
 ↓          ↓
Multi      Single
Thread     Connection
 ↓          ↓
 └────┬─────┘
      ↓
 Verification
      ↓
 Completed

This approach improves compatibility with servers that do not support multi-range downloads.

🧪 Testing

DownGo is tested against common download scenarios.

Download Engine
 PDF downloads
 MP3 downloads
 MP4 downloads
 ZIP downloads
 JPG downloads
 PNG downloads
 TXT downloads
 Large files
 HTTP Range
 HTTP 206
 Redirects
 HTTP 404
 Invalid URLs
 Pause/resume
 Connection recovery
 SHA-256 verification
Application
 Lite Mode
 Pro Mode
 System Tray
 Background startup
 Speed Tester
 Browser Bridge
 ZIP security validation
 Dependency verification
 Static release QA

Windows Defender, Microsoft Store certification and WACK validation should be performed on a real Windows test machine before release.

🛠️ Technology Stack

DownGo is built using:

Python 3.11+
PySide6 / Qt
Requests
yt-dlp
HTTP/HTTPS
Windows APIs
Microsoft Defender integration
Chrome/Edge Manifest V3
💻 Requirements
Recommended
Windows 10 or Windows 11
4 GB RAM+
Dual-core CPU+
Internet connection
Lite Mode

Designed for lower-resource systems:

1 GB+ RAM
Older dual-core CPUs
Low-power laptops
🚀 Installation
Run from Source

Clone the repository:

git clone https://github.com/YOUR_USERNAME/DownGo-FastDownloadManager.git
cd DownGo-FastDownloadManager

Install dependencies:

python -m pip install -r requirements.txt

Run:

python main.py
🔨 Build Windows Release

Run:

build_installer.bat

The build script verifies dependencies before attempting installation.

Expected output:

[PASS] Python dependencies
[PASS] Gumroad configuration
[PASS] Release static QA
[PASS] Application build
[PASS] Installer build
🔐 Security & Privacy

Never commit private credentials to GitHub.

Do not publish:

API keys
Private tokens
Passwords
Signing certificates
Customer license data
Private configuration files

If you discover a security vulnerability, please report it privately instead of opening a public issue.

See SECURITY.md.

🐛 Bug Reports

Please include:

DownGo version:
Windows version:
CPU:
RAM:
File type:
Download protocol:
Lite Mode: ON/OFF
Pro Mode: ON/OFF
Browser: Chrome/Edge/Other
Error message:
Steps to reproduce:

Do not include private URLs, passwords or license keys.

🗺️ Roadmap
 Adaptive thread scaling
 Improved bandwidth scheduling
 Advanced download categories
 Better browser integration
 More archive formats
 Improved accessibility
 Additional languages
 Advanced network diagnostics
 Performance profiling for low-RAM systems
🤝 Contributing

Contributions and bug reports are welcome.

Before submitting a pull request:

Reproduce the issue.
Check existing issues.
Explain the proposed change.
Test the change locally.
Avoid committing secrets or credentials.
📜 License

See LICENSE for the applicable license terms.

⭐ Support DownGo

If you find DownGo useful:

⭐ Star the repository
🐛 Report reproducible bugs
💡 Suggest features
🔧 Contribute improvements
📢 Share the project

