#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#ifndef SourceExe
  #define SourceExe "..\..\dist\PS-Sezhao.exe"
#endif
#ifndef InstallHtml
  #define InstallHtml "INSTALL.zh-CN.html"
#endif
#ifndef OutputDir
  #define OutputDir "."
#endif

[Setup]
AppId={{C81D47B0-59A2-4DB7-9DA5-7A4A7AF3D32A}
AppName=PS-Sezhao
AppVersion={#MyAppVersion}
AppPublisher=SnailJOSS
DefaultDirName={localappdata}\Programs\PS-Sezhao
DefaultGroupName=PS-Sezhao
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=PS-Sezhao-Installer-Windows-x64-v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\PS-Sezhao.exe
SetupLogging=yes
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："; Flags: unchecked

[Files]
Source: "{#SourceExe}"; DestDir: "{app}"; DestName: "PS-Sezhao.exe"; Flags: ignoreversion
Source: "{#InstallHtml}"; DestDir: "{app}"; DestName: "安装说明.html"; Flags: ignoreversion

[Dirs]
Name: "{app}\project"; Flags: uninsneveruninstall
Name: "{app}\lut"; Flags: uninsneveruninstall

[Icons]
Name: "{group}\PS-Sezhao"; Filename: "{app}\PS-Sezhao.exe"
Name: "{group}\安装说明"; Filename: "{app}\安装说明.html"
Name: "{autodesktop}\PS-Sezhao"; Filename: "{app}\PS-Sezhao.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\PS-Sezhao.exe"; Description: "启动 PS-Sezhao"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  MarkerPath: String;
begin
  if CurStep = ssPostInstall then
  begin
    MarkerPath := ExpandConstant('{app}\.ps-sezhao-portable');
    SaveStringToFile(MarkerPath,
      'PS-Sezhao portable data root. Keep project and lut beside the application.' + #13#10,
      False);
  end;
end;
