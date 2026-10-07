; Instalador de PULSO (Inno Setup 6). Lo compila build.bat; requiere dist\PulsoDigital\ (versión en carpeta).

#define MyAppName "PULSO"
; build.bat pasa la versión leída de app.py (/DMyAppVersion=x.y.z)
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#define MyAppPublisher "PULSO"
#define MyAppExeName "PulsoDigital.exe"

[Setup]
AppId={{8F3C2A51-6B7D-4E2A-9C1F-5D4B3A2E1F10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\PULSO
DefaultGroupName=PULSO
DisableProgramGroupPage=yes
; Se instala para el usuario actual: no pide permisos de administrador
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=PULSO_Setup_{#MyAppVersion}
SetupIconFile=..\icono.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
; Al actualizar, cierra la app abierta; la vuelve a abrir la entrada [Run] de modo silencioso
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\PulsoDigital\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PULSO"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,PULSO}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\PULSO"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,PULSO}"; Flags: nowait postinstall skipifsilent
; Actualización automática (instalador lanzado en silencio desde la app): reabrir PULSO al terminar
Filename: "{app}\{#MyAppExeName}"; Flags: nowait; Check: WizardSilent
