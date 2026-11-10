<div align="center">

  <img src="soundup.png" alt="SoundUp Banner" width="180" style="filter: drop-shadow(0px 10px 20px rgba(0, 150, 255, 0.4));" />

  # ⚡ SOUNDUP ⚡
  ### *Quebre a barreira dos 100%. O amplificador definitivo para Windows.*

  [![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011%20(x64)-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/henrique-jfp/SoundUp)
  [![Engine](https://img.shields.io/badge/Engine-Equalizer%20APO%201.4.2-FF6F00?style=for-the-badge&logo=soundcharts&logoColor=white)](https://sourceforge.net/projects/equalizerapo/)
  [![Core](https://img.shields.io/badge/Built%20With-Python%203.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
  [![Installer](https://img.shields.io/badge/Installer-WiX%20Toolset%20v3.14-5C2D91?style=for-the-badge&logo=visualstudio&logoColor=white)](https://wixtoolset.org/)
  [![License](https://img.shields.io/badge/License-MIT-success?style=for-the-badge)](LICENSE)

  <p align="center">
    <b>Ganho analógico puro de até 300%. Sem drivers kernel instáveis. Zero latência perceptível.</b>
  </p>

  <a href="[release/SoundUpSetup.exe](https://github.com/henrique-jfp/SoundUp/releases/latest/download/SoundUpSetup.exe)">
    <img src="https://img.shields.io/badge/⬇️_DOWNLOAD_SOUNDUP-SETUP.EXE-2ea44f?style=for-the-badge&logo=windows&logoColor=white" height="42">
  </a>

  <br/><br/>

  [🎬 O Manifesto](#-o-manifesto) •
  [✨ Recursos de Destaque](#-recursos-de-destaque) •
  [🏛️ Engenharia & Arquitetura](#️-engenharia--arquitetura) •
  [🚀 Guia Rápido de Instalação](#-guia-rápido-de-instalação) •
  [🛠️ Guia do Desenvolvedor](#️-guia-do-desenvolvedor) •
  [☕ Apoie o Projeto](#-apoie-o-desenvolvimento)

---

</div>

## 🎬 O Manifesto

> *"Quantas vezes você colocou o volume do Windows no 100%, colocou fones ou ligou suas caixas de som e o áudio continuava sussurrado, inaudível ou abafado?"*

O **SoundUp** nasceu para exterminar esse problema. Desenvolvido para entregar **ganho de pré-amplificação de 100% até 300%**, ele atua diretamente sobre o subsistema de áudio do Windows através de **Audio Processing Objects (APO)**. 

Diferente de amplificadores genéricos que injetam distorções ou requerem instalação de drivers instáveis sem assinatura digital, o **SoundUp** trabalha em harmonia nativa com o Windows: rápido, cirúrgico, elegante e discreto.

---

## ✨ Recursos de Destaque

<table>
  <tr>
    <td width="50%">
      <h3>🔊 Ganho Linear até 300%</h3>
      <p>Controle dinâmico de pré-amplificação (PreAmp dB). Multiplique o volume de chamadas, filmes, jogos e vídeos sem quebrar a proporção do mixer do Windows.</p>
    </td>
    <td width="50%">
      <h3>🛡️ Zero Driver Kernel (Segurança Total)</h3>
      <p>O SoundUp <b>não injeta drivers proprietários</b>. Ele orquestra o motor do respeitado <i>Equalizer APO</i>, garantindo integridade de sistema sem risco de tela azul.</p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>🕶️ Modo Furtivo (System Tray)</h3>
      <p>Minimiza silenciosamente ao lado do relógio do Windows na bandeja de notificações. Dois cliques restauram a interface em milissegundos.</p>
    </td>
    <td width="50%">
      <h3>📦 Instalador Bundle Inteligente</h3>
      <p>Construído com <b>WiX Toolset (Burn)</b>: detecta automaticamente a presença do Equalizer APO e providencia sua instalação encadeada sem dor de cabeça.</p>
    </td>
  </tr>
</table>

---

## 🏛️ Engenharia & Arquitetura

O SoundUp desacopla a interface de controle do motor de áudio, alterando arquivos de ganho em tempo real sem interrupção de fluxo:

```mermaid
flowchart TD
    subgraph UI [" 🖥️ Camada SoundUp "]
      GUI[SoundUp GUI / Slider 100%-300%] --> Controller[Controlador PreAmp]
      Controller --> Tray[System Tray Daemon pystray]
      Controller --> TargetFile[Arquivo de Ganho %LOCALAPPDATA%]
    end

    subgraph OS_Audio [" 🎵 Pipeline de Áudio Windows "]
      MediaApp[Spotify / YouTube / Jogos] --> WASAPI[Windows Audio Engine]
      TargetFile -. Configura em Tempo Real .-> APOEngine[Equalizer APO - Audio Processing Object]
      WASAPI --> APOEngine
      APOEngine --> Hardware[🔊 Caixas de Som / Fones / DAC]
    end

    style GUI fill:#1f6feb,stroke:#388bfd,stroke-width:2px,color:#fff
    style APOEngine fill:#238636,stroke:#2ea44f,stroke-width:2px,color:#fff
    style Hardware fill:#8957e5,stroke:#a371f7,stroke-width:2px,color:#fff
