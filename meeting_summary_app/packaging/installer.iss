; Inno Setup: קובץ התקנה אחד (Setup.exe) לסיכום ישיבה. מתקין למשתמש הנוכחי, ללא הרשאות מנהל.
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppName "סיכום ישיבה"
#define MyAppExe "MeetingSummary.exe"

[Setup]
AppId={{6F0C2B7E-4D1A-4C8B-9E52-3A7D9B1F4E21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Lior Agay
DefaultDirName={localappdata}\Programs\MeetingSummary
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
OutputDir=..\dist
OutputBaseFilename=MeetingSummary-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExe}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "hebrew"; MessagesFile: "compiler:Languages\Hebrew.isl"

[Files]
Source: "..\dist\MeetingSummary\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"
Name: "{usersendto}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"
Name: "{group}\הכנה ראשונית"; Filename: "{app}\{#MyAppExe}"; Parameters: "--setup"; WorkingDir: "{app}"
Name: "{group}\הנחיות הסיכום (עריכה)"; Filename: "{localappdata}\MeetingSummary\summary_prompt.txt"
Name: "{group}\הסרת {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExe}"; Parameters: "--setup"; Description: "הכנה ראשונית: התקנת Claude Code, התחברות והורדת מודל התמלול (מומלץ)"; Flags: postinstall
