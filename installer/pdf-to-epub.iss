#ifndef AppVersion
  #define AppVersion "0.12.1"
#endif
#ifndef SourceRoot
  #define SourceRoot ".."
#endif
#ifndef OutputDirectory
  #define OutputDirectory "..\release-assets"
#endif

#define AppName "PDF to EPUB OCR"
#define AppPublisher "quby1845"
#define AppUrl "https://github.com/quby1845/pdf-to-epub"
#define AppIdValue "{{4E0AF227-C130-4B64-8F7F-47A0C8B23E80}"

[Setup]
AppId={#AppIdValue}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}/issues
AppUpdatesURL={#AppUrl}/releases/latest
DefaultDirName={localappdata}\Programs\PDF to EPUB OCR
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
WizardStyle=modern
WizardResizable=yes
SetupLogging=yes
Compression=lzma2/ultra64
SolidCompression=yes
OutputDir={#OutputDirectory}
OutputBaseFilename=pdf-to-epub-ocr-v{#AppVersion}-windows-setup
UninstallDisplayName={#AppName}
UninstallDisplayIcon={sys}\shell32.dll,70
AppModifyPath="{sys}\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "{app}\installer\maintenance.ps1"
CloseApplications=yes
RestartApplications=no
ChangesEnvironment=no
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=Local GPU-accelerated PDF to EPUB OCR installer
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}
VersionInfoCopyright=Copyright (c) 2026 quby1845

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#SourceRoot}\src\*"; DestDir: "{app}\src"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceRoot}\installer\maintenance.ps1"; DestDir: "{app}\installer"; Flags: ignoreversion
Source: "{#SourceRoot}\installer\uninstall-cleanup.ps1"; DestDir: "{app}\installer"; Flags: ignoreversion
Source: "{#SourceRoot}\setup.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\launch.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\pyproject.toml"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""{app}\launch.ps1"""; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 70; Comment: "Convert scanned PDFs into reflowable e-books"
Name: "{autoprograms}\{#AppName} Maintenance"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""{app}\installer\maintenance.ps1"""; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 167; Comment: "Repair, update, or uninstall PDF to EPUB OCR"
Name: "{autodesktop}\{#AppName}"; Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""{app}\launch.ps1"""; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 70; Tasks: desktopicon; Comment: "Convert scanned PDFs into reflowable e-books"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""{app}\launch.ps1"""; WorkingDir: "{app}"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent runasoriginaluser

[UninstallRun]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""{app}\installer\uninstall-cleanup.ps1"""; WorkingDir: "{app}"; Flags: runhidden waituntilterminated

[Code]
procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpWelcome then
    WizardForm.WelcomeLabel2.Caption :=
      'Setup installs the desktop application and validates the GPU OCR runtime.' + #13#10 + #13#10 +
      'Running Setup again safely updates or repairs the existing installation.';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  PowerShellPath: String;
  SetupArguments: String;
begin
  if CurStep = ssPostInstall then begin
    SaveStringToFile(ExpandConstant('{app}\version.txt'), '{#AppVersion}' + #13#10, False);
    WizardForm.StatusLabel.Caption :=
      'Installing and validating GPU components. This can take 10-30 minutes...';
    PowerShellPath := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
    SetupArguments :=
      '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\setup.ps1') +
      '" -Operation Install -SkipShortcuts -LogPath "' +
      ExpandConstant('{localappdata}\PDF-to-EPUB-OCR\logs\setup.log') + '"';
    if (not Exec(PowerShellPath, SetupArguments, ExpandConstant('{app}'), SW_HIDE,
      ewWaitUntilTerminated, ResultCode)) or (ResultCode <> 0) then
      RaiseException(
        'The GPU runtime could not be installed or repaired. Setup log: ' +
        ExpandConstant('{localappdata}\PDF-to-EPUB-OCR\logs\setup.log'));
  end;
end;
