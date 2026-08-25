; ============================================================
; DownGo 3.2 Professional Windows Installer
; Inno Setup 6
; ============================================================

#define MyAppName "DownGo"
#define MyAppVersion "3.2.0"
#define MyAppPublisher "DownGo"
#define MyAppExeName "DownGo.exe"

[Setup]
AppId={{8E7D1A8C-3E75-4E9A-9C30-7F6C6A9B8D32}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={localappdata}\Programs\DownGo
DefaultGroupName=DownGo

DisableProgramGroupPage=yes
AllowNoIcons=yes

OutputDir=installer
OutputBaseFilename=DownGo-Setup-v{#MyAppVersion}

SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

Compression=lzma2
SolidCompression=yes
WizardStyle=modern

PrivilegesRequired=lowest

CloseApplications=yes
RestartApplications=no

VersionInfoVersion={#MyAppVersion}
VersionInfoDescription=DownGo Windows Download Manager
VersionInfoProductName=DownGo
VersionInfoCompany={#MyAppPublisher}
VersionInfoCopyright=Copyright (C) 2026 DownGo


[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked
Name: "startup"; Description: "Start DownGo with Windows"; GroupDescription: "Additional options:"; Flags: unchecked


[Files]
Source: "dist\DownGo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "browser_extension\*"; DestDir: "{app}\browser_extension"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion


[Icons]
Name: "{group}\DownGo"; Filename: "{app}\DownGo.exe"; WorkingDir: "{app}"; IconFilename: "{app}\icon.ico"
Name: "{userdesktop}\DownGo"; Filename: "{app}\DownGo.exe"; WorkingDir: "{app}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon
Name: "{userstartup}\DownGo"; Filename: "{app}\DownGo.exe"; WorkingDir: "{app}"; IconFilename: "{app}\icon.ico"; Tasks: startup


[Run]
Filename: "{app}\DownGo.exe"; Description: "Launch DownGo"; Flags: nowait postinstall skipifsilent


[UninstallDelete]
Type: filesandordirs; Name: "{app}\browser_extension"


[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;