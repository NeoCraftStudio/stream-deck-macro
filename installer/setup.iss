; Installer for NeoCraft Macro Desk.
; Per-user install (no admin/UAC prompt needed) — installs to the current
; user's LocalAppData\Programs, same convention as apps like VS Code/Discord.
; Config lives in %APPDATA%\NeoCraft Macro Desk\config.json (handled by the
; app itself, not this installer) so it survives updates and uninstalls.

#define MyAppName "NeoCraft Macro Desk"
#define MyAppVersion "4.5.0"
#define MyAppExeName "NeoCraft Macro Desk.exe"

[Setup]
AppId={{B6C1B6C0-6C1E-4B2E-9D3E-3F0E7B9B6C10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist_installer
OutputBaseFilename=NeoCraft-Macro-Desk-Setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
; InfoBeforeFile puts an "Information" page right after the welcome page. It
; explains the SmartScreen warning the user has already seen by then (the
; warning fires before this installer can run at all, so it can only be
; explained after the fact — the README is where it's explained *before*),
; and sets expectations about which features need third-party software.
; InfoAfterFile adds a final page explaining the optional virtual audio
; cable needed to send key sounds into Discord. It is a separate page from
; the one above because it is only relevant AFTER installing, and because
; bundling VB-CABLE itself would be redistribution, which needs a paid
; licence from VB-Audio. Linking is free, so the installer links.
Name: "english"; MessagesFile: "compiler:Default.isl"; InfoBeforeFile: "info_en.txt"; InfoAfterFile: "vbcable_en.txt"
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"; InfoBeforeFile: "info_pt.txt"; InfoAfterFile: "vbcable_pt.txt"

[CustomMessages]
english.OpenVbCable=Open the VB-CABLE download page (only needed for sound in Discord)
brazilianportuguese.OpenVbCable=Abrir a página de download do VB-CABLE (só precisa para som no Discord)

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\NeoCraft Macro Desk\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Registry]
; The app writes its own HKCU Run entry (set_autostart in app.py), so this
; must NOT create or touch it at install time - ValueType: none does nothing
; on install. It exists only for uninsdeletevalue: without it, uninstalling
; left the Run entry behind pointing at the exe that had just been deleted,
; and Windows tried to launch a missing file at every boot. Found on
; 2026-10-12 by actually uninstalling and looking at what was left, which no
; earlier release had done.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "NeoCraft Macro Desk"; ValueType: none; Flags: uninsdeletevalue

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent
; Unchecked by default: most people do not need it, and an unexpected browser
; window at the end of an install is worse than one extra click for those who do.
Filename: "https://vb-audio.com/Cable/"; Description: "{cm:OpenVbCable}"; Flags: nowait postinstall skipifsilent shellexec unchecked
