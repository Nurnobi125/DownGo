# DownGo 4.0.7 — Fast & Lightweight Windows Download Manager

<p align="center">
  <img src="icon.ico" width="120" height="120" alt="DownGo Logo">
</p>

<h1 align="center">DownGo 4.0.7</h1>

<p align="center">
  <b>Fast. Lightweight. Reliable.</b>
</p>

<p align="center">
  A modern Windows download manager with multi-connection acceleration,
  pause & resume, browser integration, download recovery, security scanning,
  speed testing, system-tray support and Lite Mode.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-4.0.7-blue?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/PySide6-6.x-green?style=flat-square" alt="PySide6">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%2F11-lightgrey?style=flat-square&logo=windows" alt="Windows">
  <img src="https://img.shields.io/badge/Status-Active%20Development-success?style=flat-square" alt="Status">
</p>

---

## 📖 About DownGo

**DownGo** is a fast and lightweight download manager designed for Windows 10 and Windows 11.

It focuses on three things:

* ⚡ Download performance
* 🛡️ Reliability and safer download handling
* 🪶 Low system-resource usage

When a download server supports HTTP Range requests, DownGo can split a file into multiple connections to improve download throughput.

When Range requests are unavailable, DownGo automatically falls back to a compatible single-connection download.

DownGo also provides pause/resume, retry and recovery mechanisms, persistent download history, browser integration, system-tray operation and a dedicated Lite Mode for lower-end computers.

---

# ✨ Features

## ⚡ Multi-Connection Download Acceleration

DownGo can use multiple HTTP connections when supported by the remote server.

### Features

* Multi-connection downloading
* HTTP Range support
* HTTP `206 Partial Content` validation
* Automatic server capability detection
* Automatic single-connection fallback
* Configurable connection count
* Real-time speed monitoring
* ETA calculation
* Large-file support
* Per-download connection monitoring

### Smart Download Flow

```text
Download URL
      ↓
Server Detection
      ↓
Range Supported?
   ↙         ↘
 YES         NO
 ↓            ↓
Multi       Single
Connection  Connection
 ↓            ↓
 └──────┬─────┘
        ↓
   Verification
        ↓
     Complete
```

> Multi-connection performance depends on the server, network conditions, bandwidth limitations and HTTP server configuration.

---

# 📡 Live Download Monitor

Monitor active downloads directly from the DownGo interface.

Example:

```text
┌─────────────────────────────────────────┐
│ 📡 LIVE DOWNLOAD MONITOR                │
├─────────────────────────────────────────┤
│ Ubuntu.iso                               │
│ ████████████████░░░░  78%               │
│                                         │
│ Speed:       8.4 MB/s                   │
│ ETA:         00:42                      │
│ Threads:     16 / 16                    │
│ Mode:        Multi-Range                │
│ Status:      Downloading                │
└─────────────────────────────────────────┘
```

The monitor can display:

* Current file
* Download percentage
* Current speed
* ETA
* Active connections
* Connection mode
* Download status

---

# ⏯️ Pause & Resume

DownGo is designed to handle interrupted downloads.

Supported functionality includes:

* Pause downloads
* Resume downloads
* Resume after application restart
* Retry failed connections
* Recover interrupted downloads
* Connection recovery
* Automatic retry
* Retry backoff
* Persistent download state

Resume behavior depends on server support for partial/range requests.

---

# 🔄 Smart Error & Retry Engine

DownGo can automatically recover from common temporary network failures.

Examples include:

```text
Connection timeout
Network interruption
HTTP 408
HTTP 429
HTTP 500
HTTP 502
HTTP 503
HTTP 504
Temporary connection failures
Redirect responses
Unsupported Range requests
```

The application attempts recovery without unnecessarily restarting the entire download whenever possible.

> Retry behavior can vary depending on the remote server and HTTP response.

---

# 🪶 Lite Mode

DownGo includes a dedicated **Lite Mode** for computers with limited hardware resources.

Lite Mode is available to both Free and Pro users.

### Designed for

* 1–4 GB RAM systems
* Older Intel/AMD processors
* Older laptops
* Low-power PCs
* Systems running multiple applications

### Lite Mode optimizations

* Reduced background polling
* Reduced UI refresh frequency
* Reduced animations
* Lower connection limits
* Reduced HTTP connection activity
* Reduced unnecessary CPU activity
* Reduced visual overhead

### Normal Mode

```text
Full UI
   ↓
Animations
   ↓
Higher refresh rate
   ↓
Full monitoring
```

### Lite Mode

```text
Reduced UI activity
   ↓
Reduced animations
   ↓
Reduced background polling
   ↓
Lower resource usage
```

Lite Mode does **not** disable DownGo's core download functionality.

---

# 🌐 Browser Integration

DownGo can integrate with supported desktop browsers through a local browser bridge.

### Architecture

```text
Chrome / Edge
      ↓
DownGo Browser Extension
      ↓
127.0.0.1:8765
      ↓
DownGo Browser Bridge
      ↓
Download Manager
```

### Supported

* Google Chrome
* Microsoft Edge
* Manifest V3 extension
* Local browser communication
* Download URL handoff
* Download interception where supported

The browser extension communicates with the locally running DownGo application.

---

# 📁 File Support

DownGo can handle common downloadable file types.

### 📄 Documents

* PDF
* TXT
* CSV
* DOC
* DOCX
* XLS
* XLSX
* PPT
* PPTX

### 🖼️ Images

* JPG
* JPEG
* PNG
* GIF
* WEBP
* SVG

### 🎵 Audio

* MP3
* WAV
* FLAC
* OGG
* M4A

### 🎬 Video

* MP4
* MKV
* WEBM
* MOV
* AVI

### 📦 Archives

* ZIP
* 7Z
* TAR
* GZ

Actual download support primarily depends on the URL and remote server rather than the file extension.

---

# 📦 Automatic ZIP Extraction

For supported ZIP downloads, DownGo can optionally extract archives after download validation.

### Features

* Automatic ZIP detection
* Destination-folder handling
* Archive validation
* Path traversal protection
* Corrupt archive handling
* Security scanning before extraction where configured

DownGo does **not intentionally execute extracted files automatically**.

ZIP extraction is performed using protected destination paths to reduce path traversal risks.

---

# 🛡️ Security

Security is an important part of DownGo's download workflow.

Where supported and configured, DownGo can use Windows security functionality to scan downloaded files.

### Example workflow

```text
Download
   ↓
SHA-256 Verification
   ↓
Security Scan
   ↓
Clean?
 ┌───────┴────────┐
 YES              NO
 ↓                 ↓
Continue           Block/Warning
 ↓
Optional Extraction
 ↓
Complete
```

### Security features

* SHA-256 verification
* Download validation
* Windows security integration where available
* ZIP path-traversal protection
* Safer archive extraction
* No intentional automatic execution of downloaded programs

> Antivirus availability, scan results and Windows security behavior depend on the user's Windows configuration and installed security software.

DownGo should not be considered a replacement for dedicated antivirus software.

---

# 📊 Built-in Internet Speed Test

DownGo includes a lightweight network speed testing feature.

Depending on the configured test service, it can measure:

* Latency / ping
* Download throughput
* Upload throughput
* Connection status
* Test progress

The speed test runs asynchronously so the main interface remains responsive.

> Speed-test results can vary based on server location, network congestion and ISP conditions.

---

# 🗂️ Download Queue & History

DownGo maintains persistent download information between application sessions.

### Includes

* Download queue
* Active downloads
* Completed downloads
* Failed downloads
* Download history
* Resume information
* Persistent task state
* File categorization
* Download status tracking

---

# 🖥️ System Tray & Background Mode

DownGo can operate from the Windows system tray.

When background startup is enabled:

```text
Windows Starts
      ↓
DownGo Starts
      ↓
Background Mode
      ↓
System Tray
      ↓
Main Window Remains Closed
```

The main window can be opened from the tray when required.

This is useful for users who want DownGo available without opening the main interface during Windows startup.

---

# 💎 DownGo Pro

DownGo is available in **Free and Pro editions**.

Pro is designed for users who need additional download-management functionality.

### Pro features may include

* Higher connection limits
* Advanced acceleration controls
* Advanced download controls
* Advanced scheduling
* Additional monitoring
* Premium interface features
* Advanced extraction workflow
* Additional Pro-only configuration options

> Exact Pro features depend on the specific DownGo release and license configuration.

### Licensing

Pro activation is handled through DownGo's licensing system.

A valid Pro license may be required for Pro-only functionality.

---

# 🧠 Smart Download Strategy

DownGo does not blindly use the maximum number of connections for every server.

Instead, the engine determines whether the server can support range-based downloading.

```text
URL
 ↓
Server Capability Detection
 ↓
HTTP Range Support?
 ↓
┌───────────────┐
│               │
YES             NO
│               │
Multi           Single
Connection      Connection
│               │
└───────┬───────┘
        ↓
   Download
        ↓
   Verification
        ↓
    Complete
```

This improves compatibility with servers that do not support HTTP Range requests.

---

# 🧪 Testing

DownGo should be tested against multiple download scenarios before each production release.

## Download Engine

* PDF downloads
* MP3 downloads
* MP4 downloads
* ZIP downloads
* JPG downloads
* PNG downloads
* TXT downloads
* Large files
* HTTP Range
* HTTP 206
* HTTP redirects
* HTTP 404 handling
* Invalid URLs
* Pause/resume
* Connection recovery
* Retry handling
* SHA-256 verification

## Application

* Lite Mode
* Free Mode
* Pro Mode
* System Tray
* Background startup
* Speed Tester
* Browser Bridge
* ZIP extraction
* ZIP security validation
* Dependency verification
* Persistent download state
* Static release QA

## Windows Release Validation

Before publishing a production release, perform testing on a clean Windows 10/11 environment.

Recommended validation:

* Windows Defender
* Microsoft Store certification requirements
* Windows App Certification Kit (WACK)
* Installer installation/uninstallation
* Upgrade from previous version
* Application startup
* Firewall/network behavior
* Browser extension communication
* File permissions
* Windows startup behavior

---

# 🛠️ Technology Stack

DownGo is built using:

* Python 3.11+
* PySide6 / Qt
* Requests
* yt-dlp where applicable
* HTTP / HTTPS
* Windows APIs
* Windows security integrations
* Chrome Manifest V3
* Microsoft Edge Manifest V3

Third-party libraries remain subject to their respective licenses and terms.

---

# 💻 System Requirements

## Minimum

* Windows 10 or later
* 1 GB RAM
* Dual-core CPU
* Internet connection

## Recommended

* Windows 10 / Windows 11
* 4 GB RAM or more
* Dual-core CPU or better
* SSD storage recommended

## Lite Mode

Lite Mode is specifically designed for lower-resource computers.

```text
1 GB+ RAM
Older dual-core CPU
Low-power laptop
Limited background resources
```

Actual resource usage depends on the number of active downloads, connection count, UI refresh rate and other enabled features.

---

# 🚀 Installation

## Option 1 — Windows Installer

Download the latest official Windows installer from the project's release page.

Run the installer and follow the setup instructions.

After installation:

```text
Start Menu
    ↓
DownGo
    ↓
Launch
```

---

## Option 2 — Run From Source

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/DownGo-FastDownloadManager.git
cd DownGo-FastDownloadManager
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run:

```bash
python main.py
```

---

# 🔨 Build Windows Release

The project can be packaged into a Windows executable and installer.

Example:

```text
Source Code
     ↓
Dependency Validation
     ↓
Static QA
     ↓
Application Build
     ↓
Executable Validation
     ↓
Installer Build
     ↓
Release Package
```

Example build output:

```text
[PASS] Python environment
[PASS] Dependencies
[PASS] Application configuration
[PASS] Static QA
[PASS] Security checks
[PASS] Application build
[PASS] Installer build
[PASS] Release package
```

> Release builds should be performed in a clean Windows build environment.

---

# 🔐 Security & Privacy

DownGo is designed to minimize unnecessary collection of user information.

Do not commit private credentials to the repository.

Never publish:

```text
API keys
Private tokens
Passwords
Signing certificates
Private license data
Customer information
Production secrets
```

Use environment variables or secure configuration for private credentials.

If you discover a security vulnerability, please report it privately rather than publicly exposing the vulnerability.

See:

```text
SECURITY.md
```

for the project's security reporting process.

---

# 🐛 Bug Reports

When reporting a bug, please provide:

```text
DownGo version:
Windows version:
CPU:
RAM:
File type:
Download protocol:
Lite Mode: ON/OFF
Pro Mode: ON/OFF
Browser:
Error message:
Steps to reproduce:
```

### Please do NOT include

* Passwords
* License keys
* Private URLs
* Personal information
* API keys
* Authentication tokens

---

# 🗺️ Roadmap

Planned improvements may include:

* Adaptive connection scaling
* Improved bandwidth scheduling
* Advanced download categories
* Improved browser integration
* Additional archive support
* Accessibility improvements
* Additional languages
* Advanced network diagnostics
* Low-RAM performance profiling
* Improved download recovery
* Advanced queue management
* Performance optimization

Roadmap items are subject to change.

---

# 🤝 Contributing

Contributions, suggestions and reproducible bug reports are welcome.

Before submitting a pull request:

1. Reproduce the issue.
2. Search existing issues.
3. Explain the proposed change.
4. Test your changes locally.
5. Avoid committing secrets.
6. Keep changes focused.
7. Update documentation when necessary.

---

# 📜 License

DownGo is distributed under the license included in this repository.

See:

```text
LICENSE
```

for the complete terms.

Third-party dependencies may have separate licenses and notices.

---

# ⭐ Support DownGo

If you find DownGo useful:

⭐ Star the repository

🐛 Report reproducible bugs

💡 Suggest features

🔧 Contribute improvements

📢 Share DownGo with others

---

# 📦 Commercial Edition

DownGo Pro may be distributed commercially through authorized sales channels.

For commercial purchases, licensing and activation information, follow the official product instructions provided with the purchase.

The commercial edition does not grant ownership of the DownGo source code unless explicitly stated in the applicable license.

---

# ⚠️ Important Disclaimer

DownGo is provided for legitimate downloading and file-management purposes.

Users are responsible for ensuring that downloaded content is legally obtained and that they comply with applicable laws, copyright requirements and website terms.

DownGo does not grant permission to download copyrighted or restricted material without authorization.

---

<p align="center">
  <b>DownGo 4.0.7</b><br>
  Fast • Lightweight • Reliable
</p>
