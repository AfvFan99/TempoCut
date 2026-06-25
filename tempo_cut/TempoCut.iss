; TempoCut.iss
; Inno Setup script — builds a real Windows installer (TempoCut_Setup.exe)
;
; Requires: Inno Setup 6 (free) -> https://jrsoftware.org/isinfo.php
;
; Build order:
;   1. pyinstaller tempocut.spec          (produces dist\TempoCut\TempoCut.exe + deps)
;   2. Open this .iss file in Inno Setup Compiler and click Compile
;      (or run from command line: iscc TempoCut.iss)
;   3. Output\TempoCut_Setup.exe is your shareable installer.

#define MyAppName "TempoCut"
#define MyAppVersion "1.2"
#define MyAppPublisher "TempoCut"
#define MyAppExeName "TempoCut.exe"

[Setup]
AppId={{8F2C1A4E-9B3D-4E7A-BA12-5C6D8E9F0A1B}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Change this to wherever you want the installer .exe to land:
OutputDir=Output
OutputBaseFilename=TempoCut_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Uncomment and point at an .ico if you make one:
; SetupIconFile=tempocut.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
; Pulls everything PyInstaller produced in dist\TempoCut\ (the exe + all deps + companion scripts)
Source: "dist\TempoCut\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function FFmpegFound(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/C where ffmpeg', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

procedure InitializeWizard();
begin
  if not FFmpegFound() then
  begin
    MsgBox('TempoCut requires ffmpeg and ffprobe to be installed and available on your system PATH.' + #13#10 + #13#10 +
           'If you haven''t installed ffmpeg yet, download it from https://ffmpeg.org/download.html, ' +
           'extract it, and add the bin folder to your PATH before running TempoCut.',
           mbInformation, MB_OK);
  end;
end;
