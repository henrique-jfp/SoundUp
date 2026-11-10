# SoundUp

Amplificador de áudio para Windows usando Equalizer APO.

## Usuário final

Baixe [release/SoundUpSetup.exe](release/SoundUpSetup.exe) e execute como administrador.

> **Dependência:** o SoundUp precisa do Equalizer APO para funcionar. O instalador
> explica essa dependência e pede sua aceitação; se o Equalizer APO não estiver
> instalado, ele é incluído automaticamente. Cancele a instalação se não aceitar.

O instalador:

1. Detecta se o Equalizer APO já está instalado.
2. Instala o Equalizer APO oficial quando necessário.
3. Instala o SoundUp e cria atalhos no Menu Iniciar e na área de trabalho.

Na primeira abertura do SoundUp:

1. Clique em **Abrir configurador**.
2. Aceite a solicitação de administrador.
3. Marque o dispositivo de saída que será usado.
4. Confirme a configuração e reinicie o áudio ou o Windows se solicitado.
5. Volte ao SoundUp, clique em **Concluir e aplicar** e aceite a solicitação de administrador. Essa etapa permite que o SoundUp altere apenas o seu arquivo de ganho.
6. Ajuste o ganho entre 100% e 300%.

Ao minimizar a janela, o SoundUp permanece ativo como um ícone ao lado do relógio
do Windows. Clique duas vezes no ícone, ou use **Abrir SoundUp**, para voltar à janela.

## Arquivos instalados

- SoundUp: `C:\Program Files\SoundUp\SoundUp.exe`
- Equalizer APO: `C:\Program Files\EqualizerAPO\`
- Configuração do usuário: `%LOCALAPPDATA%\SoundUp\`

## Estrutura

```text
SoundUp/
├── qrcodeapoio.png             # QR Code Pix do botão "Apoie o projeto"
├── legacy/
│   ├── soundup_preamp.py       # Interface e controle do ganho
│   ├── configurar_apo.ps1      # Configuração manual opcional
│   ├── requirements.txt
│   └── dist/SoundUp.exe        # Executável usado pelo MSI
├── installer/wix/
│   ├── Product.wxs             # MSI do SoundUp
│   ├── Bundle.wxs              # Instalador SoundUp + Equalizer APO
│   └── EqualizerAPO-x64-1.4.2.exe
└── release/
    ├── SoundUpSetup.exe        # Instalador recomendado
    └── SoundUpSetup.msi        # MSI do SoundUp
```

## Desenvolvimento

Requisitos:

- Windows 10 ou 11 x64
- Python 3.11 ou superior
- WiX Toolset 3.14 para gerar os instaladores

Instale as dependências Python:

```powershell
python -m pip install -r legacy\requirements.txt
```

Para gerar o executável:

```powershell
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --windowed --onefile --name SoundUp --distpath legacy\dist --hidden-import pystray._win32 --add-data "qrcodeapoio.png;." legacy\soundup_preamp.py
```

Para gerar os instaladores atualizados, primeiro gere o MSI e depois o instalador
completo. Os dois arquivos serão escritos em `release/`:

```powershell
# SolutionDir como variável de ambiente preserva a barra final.
$env:SolutionDir = (Get-Location).Path + "\"
msbuild installer\wix\SoundUpInstaller.wixproj /p:Configuration=Release /p:Platform=x64
msbuild installer\wix\SoundUpBootstrapper.wixproj /p:Configuration=Release /p:Platform=x64
```

O instalador oficial do Equalizer APO incluído neste repositório é executado somente
quando a detecção do instalador não encontra uma instalação existente.

## Observações

- O SoundUp não instala driver próprio.
- O ganho acima de 100% só funciona nos dispositivos marcados no Configurator do Equalizer APO.
- O projeto não requer certificado de driver.
