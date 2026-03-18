; Script Final e Completo para o Projeto Centaurus
; Versão de 25 de julho de 2025 - Atualizado para build completo

#define MyAppName "Centaurus"
#define MyAppVersion "1.6"
#define MyAppPublisher "RFH/DCRIM/INI/DPA/PF"
#define MyAppExeName "Centaurus.exe"

; --- Definições para Associação de Arquivos ---
#define MyAppAssocName MyAppName + " File"
#define MyAppAssocExt ".myp"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
; Identificador único da aplicação
AppId={{8C907F18-9DF0-40E2-AF58-D70D18E2588E}

; Informações do Aplicativo e Publicador
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

; Diretório de Instalação Padrão
DefaultDirName={autopf}\{#MyAppName}

; Ícone que aparecerá em "Adicionar/Remover Programas"
UninstallDisplayIcon={app}\{#MyAppExeName}

; Configurações de Arquitetura
ArchitecturesInstallIn64BitMode=x64

; Flag para associação de arquivos
ChangesAssociations=yes

; Simplificação da página de instalação
DisableProgramGroupPage=yes

; --- INFORMAÇÕES A VERIFICAR ---
; 1. Onde o setup.exe final será salvo
OutputDir=C:\Users\andre.agsm\OneDrive - Polícia Federal
; 2. Caminho para o ícone do instalador
SetupIconFile=C:\face_system\Empacotador_Centaurus\icone.ico
; ---------------------------------

; Nome base do arquivo de setup
OutputBaseFilename=Centaurus_setup_{#MyAppVersion}

; Senha e Criptografia
Password=CENTAURUS2025
Encryption=yes

; Compatibilidade
MinVersion=6.1sp1

; Interface
WizardStyle=modern

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 0,6.1

[Files]
; Arquivo principal do aplicativo
Source: "C:\face_system\Empacotador_Centaurus\dist\Centaurus\Centaurus.exe"; DestDir: "{app}"; Flags: ignoreversion

; Pasta completa com todas as dependências
Source: "C:\face_system\Empacotador_Centaurus\dist\Centaurus\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Certificar-se de que os modelos de IA sejam instalados
Source: "C:\face_system\Empacotador_Centaurus\models\*"; DestDir: "{userappdata}\.insightface\models"; Flags: ignoreversion recursesubdirs createallsubdirs; Tasks: 

; Ícone do aplicativo
Source: "C:\face_system\Empacotador_Centaurus\icone.ico"; DestDir: "{app}"; Flags: ignoreversion

; Arquivos de configuração e documentação
Source: "C:\face_system\Empacotador_Centaurus\README.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "C:\face_system\Empacotador_Centaurus\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Registry]
; Registrar aplicação para facilitar desinstalação completa
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}"; ValueType: string; ValueName: "DisplayName"; ValueData: "{#MyAppName}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}"; ValueType: string; ValueName: "UninstallString"; ValueData: """{uninstallexe}"""; Flags: uninsdeletekey
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}"; ValueType: string; ValueName: "DisplayIcon"; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}"; ValueType: string; ValueName: "Publisher"; ValueData: "{#MyAppPublisher}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}"; ValueType: string; ValueName: "DisplayVersion"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey

[UninstallDelete]
; Limpar arquivos de configuração e modelos na desinstalação
Type: filesandordirs; Name: "{userappdata}\.insightface\models"
Type: filesandordirs; Name: "{app}"

[Code]
function InitializeSetup(): Boolean;
begin
  // Verificar se o sistema é 64-bit
  if not IsWindows64 then
  begin
    MsgBox('Este aplicativo requer Windows 64-bit.', mbError, MB_OK);
    Result := False;
    Exit;
  end;
  
  // Verificar versão do Windows
  if GetWindowsVersion < $06010000 then
  begin
    MsgBox('Este aplicativo requer Windows 7 SP1 ou superior.', mbError, MB_OK);
    Result := False;
    Exit;
  end;
  
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Criar diretório para modelos se não existir
    if not DirExists(ExpandConstant('{userappdata}\.insightface\models')) then
    begin
      ForceDirectories(ExpandConstant('{userappdata}\.insightface\models'));
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    // Limpar arquivos temporários
    if DirExists(ExpandConstant('{userappdata}\.insightface\models')) then
    begin
      DelTree(ExpandConstant('{userappdata}\.insightface\models'), True, True, True);
    end;
  end;
end;