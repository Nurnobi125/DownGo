# DownGo 3.2

Windows download manager with:

- IDM-style desktop UI
- System tray/background mode
- Multi-connection HTTP/HTTPS downloads
- Pause/resume/cancel
- Speed and ETA
- Download history
- Windows startup option
- Local browser bridge on `127.0.0.1:8765`
- Chrome/Edge Manifest V3 download interception
- Browser download is cancelled only after DownGo accepts the URL
- Better filename detection from Content-Disposition and URL
- **Pro: Custom Themes** — including Aurora Glass, a frosted/glassmorphism
  theme with translucent panels and soft gradients
- **Pro: Custom Background** — set your own background image behind the
  UI, with a one-click "↺ Default" reset back to the theme's normal look
- Soft, adaptive window — the sidebar eases itself narrower on smaller
  windows and back out again, instead of snapping abruptly

## Custom Themes & Background (Pro)

Use the theme dropdown (top toolbar) to switch looks, including the
glassmorphism-style **Aurora Glass** theme. Click **🖼️ Background** to
pick your own image to show behind the UI, and **↺ Default** to remove
it and go back to the theme's default look. Both the selected theme and
background are remembered the next time you open DownGo.

These are gated behind an active Pro license, same as the app's other
Pro controls.

## Run

```bat
python -m pip install -r requirements.txt
python main.py
```

## Build EXE

Put `icon.ico` in the project root and run:

```bat
build_exe.bat
```

## Browser extension

Start DownGo first, then load `browser_extension` as an unpacked
extension in Chrome or Edge.

The extension talks only to the local DownGo bridge.

This project handles ordinary HTTP/HTTPS downloads. It does not bypass DRM,
authentication, paywalls, signed access controls, or other restrictions.


## Professional Windows Installer

This project includes `DownGo-Setup.iss` for Inno Setup.

1. Install Inno Setup 6 on Windows.
2. Run `build_installer.bat`.
3. The result will be:
   `installer\DownGo-Setup-v3.2.0.exe`

The installer:
- Installs DownGo under Program Files
- Creates Start Menu shortcut
- Optionally creates Desktop shortcut
- Optionally starts DownGo with Windows
- Includes the browser extension files
- Uses the DownGo icon
- Provides normal Windows uninstall support

Important: the browser extension still needs to be loaded/published separately. A desktop installer cannot silently install a Chrome/Edge Web Store extension.

