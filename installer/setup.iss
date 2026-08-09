; Installer for NeoCraft Macro Desk.
; Per-user install (no admin/UAC prompt needed) — installs to the current
; user's LocalAppData\Programs, same convention as apps like VS Code/Discord.
; Config lives in %APPDATA%\NeoCraft Macro Desk\config.json (handled by the
; app itself, not this installer) so it survives updates and uninstalls.

#define MyAppName "NeoCraft Macro Desk"
#define MyAppVersion "2.1.1"
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
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\NeoCraft Macro Desk\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent
