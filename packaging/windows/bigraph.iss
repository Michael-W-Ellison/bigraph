; Inno Setup script for the Bigraph Windows installer (Inno Setup 6)
;
; Build from the PyInstaller folder build (dist\Bigraph):
;   ISCC /DAppVersion=1.0.0 /O<output folder> packaging\windows\bigraph.iss
;
; Installs for the current user by default (no administrator rights needed);
; the installer offers installing for all users instead. Uninstalling removes
; the program but not the user's keys and messages, which stay in their
; Windows key store and %APPDATA%\Bigraph until deleted in the program.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\..\dist\Bigraph"
#endif

[Setup]
; Keep AppId the same in every release, so new versions upgrade old ones
AppId={{E40AA19B-88A9-43B7-90E4-A24446FF9618}
AppName=Bigraph
AppVersion={#AppVersion}
AppPublisher=Bigraph project
AppPublisherURL=https://github.com/Michael-W-Ellison/bigraph
DefaultDirName={autopf}\Bigraph
DefaultGroupName=Bigraph
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputBaseFilename=Bigraph-Setup-{#AppVersion}-windows-x86_64
SetupIconFile=..\icons\bigraph.ico
UninstallDisplayIcon={app}\Bigraph.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Bigraph"; Filename: "{app}\Bigraph.exe"
Name: "{autodesktop}\Bigraph"; Filename: "{app}\Bigraph.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Bigraph.exe"; Description: "{cm:LaunchProgram,Bigraph}"; Flags: nowait postinstall skipifsilent
