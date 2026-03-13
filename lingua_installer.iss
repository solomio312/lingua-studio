[Setup]
AppName=Lingua
AppVersion=1.1.0
DefaultDirName={autopf}\Lingua
DefaultGroupName=Lingua
UninstallDisplayIcon={app}\Lingua.exe
Compression=lzma2
SolidCompression=yes
OutputDir=dist
OutputBaseFilename=Lingua_Installer_v1.1.0
SetupIconFile=lingua\resources\icon.ico
PrivilegesRequired=lowest
AppPublisher=Manux
AppSupportURL=https://github.com/solomio312/lingua-studio
AppUpdatesURL=https://github.com/solomio312/lingua-studio

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Normal Build (Folder-based)
Source: "dist\Lingua\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Lingua"; Filename: "{app}\Lingua.exe"
Name: "{commondesktop}\Lingua"; Filename: "{app}\Lingua.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Lingua.exe"; Description: "{cm:LaunchProgram,Lingua}"; Flags: nowait postinstall skipifsilent
