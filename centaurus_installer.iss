; ========================================
; Centaurus 2.0 - Instalador com Senha
; ========================================
; Este script cria um instalador Windows com proteção por senha
; Requer Inno Setup 6.0 ou superior
; Para compilar: iscc centaurus_installer.iss

#define MyAppName "Centaurus"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Sistema de Verificação Facial"
#define MyAppExeName "Centaurus.exe"
#define MyAppIcon "icone.ico"

; Senha do instalador (ALTERE CONFORME NECESSÁRIO)
#define InstallerPassword "CENTAURUS2025"

[Setup]
; Informações básicas
AppId={{F7A3B8E4-2C9D-4E5F-A1B7-8D3C5E9F2A4C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=LICENSE.txt
OutputDir=installer_output
OutputBaseFilename=CentaurusSetup_{#MyAppVersion}
SetupIconFile={#MyAppIcon}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; Requisitos
MinVersion=10.0
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; Interface
ShowLanguageDialog=no
DisableWelcomePage=no
DisableFinishedPage=no

; Senha de instalação
Password={#InstallerPassword}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar ícone na área de trabalho"; GroupDescription: "Ícones adicionais:"; Flags: unchecked

[Files]
; Executável principal
Source: "dist\Centaurus\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Todo o conteúdo _internal (inclui modelos, DLLs, bibliotecas)
Source: "dist\Centaurus\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

; Ícone
Source: "{#MyAppIcon}"; DestDir: "{app}"; Flags: ignoreversion

; Documentação
Source: "README_V2.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "BUILD_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Menu Iniciar
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIcon}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"

; Área de trabalho (opcional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIcon}"; Tasks: desktopicon

[Run]
; Opção de executar após instalação
Filename: "{app}\{#MyAppExeName}"; Description: "Executar {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
var
  PasswordPage: TInputQueryWizardPage;
  
procedure InitializeWizard;
begin
  // Criar página de senha personalizada
  PasswordPage := CreateInputQueryPage(wpWelcome,
    'Senha de Instalação',
    'Digite a senha para continuar',
    'Este instalador requer uma senha de autorização para prosseguir.');
  PasswordPage.Add('Senha:', True);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  
  // Validar senha na página customizada
  if CurPageID = PasswordPage.ID then
  begin
    if PasswordPage.Values[0] <> '{#InstallerPassword}' then
    begin
      MsgBox('Senha incorreta. A instalação não pode continuar.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

[UninstallDelete]
; Limpar diretório de dados (opcional - descomente se desejar)
; Type: filesandordirs; Name: "{commonappdata}\Centaurus"

[Messages]
brazilianportuguese.WelcomeLabel1=Bem-vindo ao Assistente de Instalação do [name]
brazilianportuguese.WelcomeLabel2=Este instalará o [name/ver] em seu computador.%n%nÉ recomendável que você feche todos os outros aplicativos antes de continuar.
brazilianportuguese.ClickNext=Clique em Avançar para continuar ou Cancelar para sair da instalação.
brazilianportuguese.SelectDirLabel3=A instalação irá instalar [name] na seguinte pasta.
brazilianportuguese.SelectDirBrowseLabel=Para continuar, clique em Avançar. Se você deseja selecionar uma pasta diferente, clique em Procurar.
brazilianportuguese.FinishedHeadingLabel=Concluindo o Assistente de Instalação do [name]
brazilianportuguese.FinishedLabel=O [name] foi instalado em seu computador.%n%nA aplicação pode ser executada selecionando o ícone instalado.

[Registry]
; Adicionar ao PATH (opcional)
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Check: NeedsAddPath(ExpandConstant('{app}'))

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE,
    'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
    'Path', OrigPath)
  then begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
  MsgText: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    MsgText := 'Deseja remover também os dados do sistema (banco de dados e configurações)?'#13#10 +
               'Localização: C:\ProgramData\Centaurus'#13#10#13#10 +
               'Clique em Sim para remover TUDO ou Não para manter os dados.';
    
    if MsgBox(MsgText, mbConfirmation, MB_YESNO) = IDYES then
    begin
      // Remove diretório de dados
      Exec('cmd.exe', '/c rmdir /s /q "C:\ProgramData\Centaurus"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      MsgBox('Dados do sistema removidos com sucesso.', mbInformation, MB_OK);
    end;
  end;
end;
