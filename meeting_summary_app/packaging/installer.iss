; Inno Setup: קובץ התקנה אחד (Setup.exe) לסיכום ישיבה. מתקין למשתמש הנוכחי, ללא הרשאות מנהל.
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppName "מסכם הישיבות של ליאור אגאי"
#define ShortcutName "סיכום ישיבה"
#define MyAppExe "MeetingSummary.exe"

[Setup]
AppId={{6F0C2B7E-4D1A-4C8B-9E52-3A7D9B1F4E21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Lior Agay
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany=Lior Agay
VersionInfoDescription=Meeting Summary Setup
DefaultDirName={localappdata}\Programs\MeetingSummary
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=MeetingSummary-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
InfoBeforeFile=..\מה כלול בגרסה.txt
UninstallDisplayIcon={app}\{#MyAppExe}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "hebrew"; MessagesFile: "compiler:Languages\Hebrew.isl"

[Files]
Source: "..\מה כלול בגרסה.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\MeetingSummary\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userdesktop}\{#ShortcutName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"
Name: "{usersendto}\{#ShortcutName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"
Name: "{group}\{#ShortcutName}"; Filename: "{app}\{#MyAppExe}"; WorkingDir: "{app}"
Name: "{group}\הכנה ראשונית"; Filename: "{app}\{#MyAppExe}"; Parameters: "--setup"; WorkingDir: "{app}"
Name: "{group}\מה כלול בגרסה"; Filename: "{app}\מה כלול בגרסה.txt"
Name: "{group}\הנחיות הסיכום (עריכה)"; Filename: "{localappdata}\MeetingSummary\summary_prompt.txt"
Name: "{group}\הסרת {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExe}"; Parameters: "--setup"; Description: "הכנה ראשונית: בדיקה והתקנה של כל מה שחסר - Claude Code, התחברות, מודל התמלול והתראות (מומלץ)"; Flags: postinstall
