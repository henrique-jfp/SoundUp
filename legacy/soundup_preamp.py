"""SoundUp: virtual-cable pre-amplifier for Windows."""

from __future__ import annotations

import os
import ctypes
import tkinter as tk
import math
import subprocess
import sys
import time
from queue import Empty, SimpleQueue
import re
from pathlib import Path
from tkinter import messagebox, ttk

import pystray
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
from PIL import Image, ImageDraw, ImageTk


MIN_GAIN = 100
MAX_GAIN = 300
SETTINGS_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "SoundUp"
SETTINGS_FILE = SETTINGS_DIR / "settings.txt"
GAIN_FILE = SETTINGS_DIR / "gain.txt"
SETUP_COMPLETE_FILE = SETTINGS_DIR / "apo-setup-complete"
DEPENDENCY_CONSENT_FILE = SETTINGS_DIR / "equalizer-apo-consent"
APO_CONFIG = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "EqualizerAPO" / "config" / "config.txt"
APO_INCLUDE = APO_CONFIG.parent / "soundup-preamp.txt"
APO_INCLUDE_LINE = f"Include: {APO_INCLUDE}"
APO_INCLUDE_PATTERN = re.compile(
    r"^\s*Include:\s*.*soundup-preamp\.txt\s*$", re.IGNORECASE
)

GAIN_STEP = 5
HOTKEY_POLL_MS = 30
HOTKEY_HOLD_DELAY = 0.35
HOTKEY_RAMP_THRESHOLDS = (1.35, 2.35)
HOTKEY_RAMP_INTERVALS = (0.10, 0.07, 0.05)
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_UP = 0x26
VK_DOWN = 0x28
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_LMENU = 0xA4
VK_RMENU = 0xA5
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
SW_SHOWNOACTIVATE = 4
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010


class _Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _Rect(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class _MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", _Rect),
        ("rcWork", _Rect),
        ("dwFlags", ctypes.c_ulong),
    ]


class ApoNotInstalledError(RuntimeError):
    """Raised when Equalizer APO or its main configuration is missing."""


class ApoIncludeError(RuntimeError):
    """Raised when SoundUp's include cannot be added to Equalizer APO."""


class NoAudioOutputError(RuntimeError):
    """Raised when Windows has no active audio output device."""


def resource_path(filename: str) -> Path:
    """Return a bundled resource path, or the repository file during development."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    else:
        base = Path(__file__).resolve().parent.parent
    return base / filename


def endpoint_volume(device):
    """Return the endpoint-volume COM interface for the current default device."""
    # Recent pycaw versions expose the interface directly as EndpointVolume.
    endpoint = getattr(device, "EndpointVolume", None)
    if endpoint is not None:
        return endpoint

    # Compatibility path for older pycaw versions.
    interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return interface.QueryInterface(IAudioEndpointVolume)


def active_output_devices():
    return [
        device for device in AudioUtilities.GetAllDevices()
        if str(device.id).startswith("{0.0.0.00000000}.")
        and getattr(device.state, "value", 0) == 1
    ]


def key_is_down(vk: int) -> bool:
    """Return True while a virtual key is physically pressed, even unfocused."""
    return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)


class EqualizerApoController:
    """Controls SoundUp's managed Equalizer APO preamp configuration."""

    def __init__(self) -> None:
        if not APO_CONFIG.is_file():
            raise ApoNotInstalledError(
                "Equalizer APO não está instalado ou o arquivo config.txt não foi encontrado."
            )
        self.include_ready = False
        self.repaired_include = False
        try:
            self.repaired_include = self._ensure_include()
            self.include_ready = True
        except OSError:
            # The app still opens; the setup dialog will request elevation.
            self.include_ready = False

    @staticmethod
    def _ensure_include() -> bool:
        """Add SoundUp's include to config.txt, preserving other entries.

        Returns True when the file had to be repaired. Equalizer APO's
        Configurator rewrites config.txt and can drop third-party includes,
        so this runs again whenever the gain is applied.
        """
        raw = APO_CONFIG.read_bytes()
        text = raw.decode("utf-8-sig")
        newline = "\r\n" if b"\r\n" in raw else "\n"
        # Normalize before splitting: a previous write could have produced
        # "\r\r\n", which makes Equalizer APO read the Include filename with a
        # trailing "\r" and fail with ERROR_INVALID_NAME.
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = normalized.split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        matching = [
            line for line in lines if APO_INCLUDE_PATTERN.match(line)
        ]
        if len(matching) == 1 and matching[0].strip() == APO_INCLUDE_LINE:
            desired = newline.join(lines) + newline
            if text == desired:
                return False
        lines = [line for line in lines if not APO_INCLUDE_PATTERN.match(line)]
        lines.append(APO_INCLUDE_LINE)
        desired = newline.join(lines) + newline
        # newline="" prevents Python from translating the already correct
        # line endings again (which is what created "\r\r\n").
        with APO_CONFIG.open("w", encoding="utf-8", newline="") as handle:
            handle.write(desired)
        return True

    def _refresh_include(self) -> None:
        """Repair the include if another program removed or corrupted it."""
        try:
            self.repaired_include = self._ensure_include() or self.repaired_include
            self.include_ready = True
        except OSError as error:
            self.include_ready = False
            raise ApoIncludeError(
                "O SoundUp não conseguiu se registrar na configuração do "
                "Equalizer APO (config.txt). Use 'Concluir e aplicar' no "
                "SoundUp para corrigir com permissão de administrador."
            ) from error

    def set_gain(self, gain_percent: int) -> None:
        self._refresh_include()
        gain_db = 20 * math.log10(gain_percent / 100.0)
        APO_INCLUDE.write_text(
            "# SoundUp preamp (managed section)\n"
            f"Preamp: {gain_db:+.2f} dB\n"
            "PreventClipping: yes\n",
            encoding="utf-8",
        )


class SoundUpApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SoundUp - Pré-amplificador")
        self.configure(bg="#101827")
        self.resizable(False, False)
        self._apply_window_icon()
        self._closing = False
        self.startup_cancelled = False
        self._tray_icon: pystray.Icon | None = None
        self._tray_actions: SimpleQueue[str] = SimpleQueue()
        self._gain_apply_job: str | None = None
        self._save_gain_job: str | None = None
        self._overlay: tk.Toplevel | None = None
        self._overlay_job: str | None = None
        self._include_error: str | None = None
        self._suppress_slider = False
        self._hotkey_direction = 0
        self._hotkey_started_at = 0.0
        self._hotkey_next_repeat_at = 0.0
        if not self._confirm_equalizer_apo_dependency():
            self.startup_cancelled = True
            self.destroy()
            return
        self.output_devices = active_output_devices()
        if not self.output_devices:
            raise NoAudioOutputError("Nenhuma saída de áudio ativa foi encontrada.")
        self.device_by_name = {
            f"{device.FriendlyName}": device for device in self.output_devices
        }
        saved_id = self._load_device_id()
        default_device = AudioUtilities.GetSpeakers()
        selected = next(
            (device for device in self.output_devices if device.id == saved_id),
            next(
                (device for device in self.output_devices if device.id == default_device.id),
                self.output_devices[0],
            ),
        )
        self.selected_device = selected
        self.endpoint = endpoint_volume(selected)
        self.apo = EqualizerApoController()
        self.saved_gain = self._load_gain()
        self.gain = tk.IntVar(value=self.saved_gain)
        self.status = tk.StringVar()
        self._suppress_slider = True
        self._configure_style()
        self._build_ui()
        self._suppress_slider = False
        self._build_overlay()
        try:
            self.apo.set_gain(self.saved_gain)
            if self.apo.repaired_include:
                message = "Configuração do Equalizer APO restaurada automaticamente."
            else:
                message = "Equalizer APO ativo: controle direto de ganho."
            if self.saved_gain != MIN_GAIN:
                message += f" Ganho restaurado em {self.saved_gain}%."
            self.status.set(message)
        except ApoIncludeError as error:
            self._include_error = str(error)
            self.status.set(self._include_error)
        except (OSError, RuntimeError) as error:
            self.status.set(
                "Equalizer APO requer configuração inicial: "
                f"{self._friendly_error(error)}"
            )
        self._update_status()
        if not SETUP_COMPLETE_FILE.is_file() or self._include_error:
            self.after(250, self._show_setup_dialog)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Configure>", self._on_window_configure)
        self.bind("<Unmap>", self._on_window_unmap)
        self.after(100, self._process_tray_actions)
        self.after(250, self._tray_watchdog)
        self.after(HOTKEY_POLL_MS, self._poll_hotkeys)

    def _confirm_equalizer_apo_dependency(self) -> bool:
        """Ask for explicit consent before SoundUp uses Equalizer APO."""
        if DEPENDENCY_CONSENT_FILE.is_file():
            return True

        accepted = messagebox.askyesno(
            "Equalizer APO necessário",
            "O SoundUp precisa do Equalizer APO para aumentar o ganho do áudio.\n\n"
            "O instalador recomendado instala o Equalizer APO quando ele ainda não "
            "está presente. Ao continuar, você aceita usar esse componente no seu PC?\n\n"
            "Escolha Não para fechar o SoundUp sem fazer alterações.",
            icon="question",
        )
        if accepted:
            SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            DEPENDENCY_CONSENT_FILE.write_text("accepted\n", encoding="utf-8")
        return accepted

    @staticmethod
    def _load_device_id() -> str:
        try:
            return SETTINGS_FILE.read_text(encoding="utf-8").strip()
        except OSError:
            return ""

    @staticmethod
    def _load_gain() -> int:
        try:
            value = int(GAIN_FILE.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return MIN_GAIN
        return max(MIN_GAIN, min(MAX_GAIN, value))

    def _save_gain_now(self, gain: int) -> None:
        self._save_gain_job = None
        try:
            SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            GAIN_FILE.write_text(str(gain), encoding="utf-8")
        except OSError:
            pass

    def _schedule_save_gain(self, gain: int) -> None:
        if self._save_gain_job is not None:
            self.after_cancel(self._save_gain_job)
        self._save_gain_job = self.after(400, lambda: self._save_gain_now(gain))

    def _save_device_id(self) -> None:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(self.selected_device.id, encoding="utf-8")

    @staticmethod
    def _device_selector_path() -> Path | None:
        candidates = [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
            / "EqualizerAPO" / "DeviceSelector.exe",
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
            / "EqualizerAPO" / "DeviceSelector.exe",
        ]
        return next((path for path in candidates if path.is_file()), None)

    def _open_device_selector(self) -> None:
        selector = self._device_selector_path()
        if selector is None:
            messagebox.showerror(
                "Equalizer APO",
                "O Configurador do Equalizer APO não foi encontrado.",
            )
            return
        try:
            result = ctypes.windll.shell32.ShellExecuteW(
                self.winfo_id(),
                "runas",
                str(selector),
                None,
                str(selector.parent),
                1,
            )
            if result <= 32:
                raise OSError(f"código ShellExecute: {result}")
        except OSError as error:
            messagebox.showerror(
                "Não foi possível abrir o configurador",
                f"Erro ao abrir o Equalizer APO:\n{error}",
            )

    @staticmethod
    def _setup_script_path() -> Path:
        """Return the elevated setup helper installed beside SoundUp.exe."""
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent / "configurar_apo.ps1"
        return Path(__file__).resolve().with_name("configurar_apo.ps1")

    def _apply_apo_setup(self) -> None:
        """Configure Equalizer APO once with UAC, then restore normal app access."""
        script = self._setup_script_path()
        if not script.is_file():
            raise RuntimeError(
                "O auxiliar de configuração do SoundUp não foi encontrado. "
                "Reinstale o SoundUp."
            )

        escaped_script = str(script).replace("'", "''")
        command = (
            "$soundUpArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "
            f"'{escaped_script}'); "
            "$soundUpProcess = Start-Process -FilePath 'powershell.exe' "
            "-ArgumentList $soundUpArgs -Verb RunAs -Wait -PassThru; "
            "exit $soundUpProcess.ExitCode"
        )
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "A configuração com permissão de administrador foi cancelada ou falhou."
            )

    def _show_setup_dialog(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Configuração inicial")
        dialog.configure(bg="#101827")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=22, style="Window.TFrame")
        frame.grid()
        ttk.Label(
            frame,
            text="Configure sua saída de áudio",
            style="Title.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            frame,
            text=(
                "Para o SoundUp aumentar o som, o Equalizer APO precisa ser "
                "aplicado ao dispositivo selecionado."
            ),
            wraplength=430,
            justify="left",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(8, 14))
        instruction_row = 2
        if self._include_error:
            ttk.Label(
                frame,
                text=(
                    "O SoundUp foi removido da configuração do Equalizer APO. "
                    "Clique em Concluir e aplicar para registrar o SoundUp "
                    "novamente e restaurar o aumento de volume."
                ),
                wraplength=430,
                justify="left",
                style="CardText.TLabel",
            ).grid(row=instruction_row, column=0, sticky="w", pady=(0, 12))
            instruction_row += 1
        ttk.Label(
            frame,
            text=(
                "1. Clique em Abrir configurador.\n"
                "2. Marque o dispositivo de saída que está usando.\n"
                "3. Confirme e reinicie o áudio ou o Windows se solicitado.\n"
                "4. Volte aqui, clique em Concluir e aplicar e aceite a solicitação "
                "de administrador."
            ),
            wraplength=430,
            justify="left",
            style="CardText.TLabel",
        ).grid(row=instruction_row, column=0, sticky="w", pady=(0, 18))

        buttons = ttk.Frame(frame, style="Window.TFrame")
        buttons.grid(row=instruction_row + 1, column=0, sticky="e")
        ttk.Button(
            buttons,
            text="Abrir configurador",
            command=self._open_device_selector,
            style="Accent.TButton",
        ).grid(row=0, column=0, padx=(0, 8))

        def finish_setup() -> None:
            try:
                self._apply_apo_setup()
                self.apo.set_gain(self.gain.get())
                self._save_gain_now(self.gain.get())
            except (OSError, RuntimeError) as error:
                messagebox.showerror(
                    "Não foi possível concluir a configuração",
                    self._friendly_error(error),
                )
                return
            SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            SETUP_COMPLETE_FILE.write_text("configured\n", encoding="utf-8")
            self._include_error = None
            self.status.set(
                f"Configuração concluída para {self.selected_device.FriendlyName}."
            )
            dialog.destroy()

        ttk.Button(
            buttons,
            text="Concluir e aplicar",
            command=finish_setup,
        ).grid(row=0, column=1)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Window.TFrame", background="#101827")
        style.configure("Card.TFrame", background="#182438")
        style.configure(
            "Title.TLabel", background="#101827", foreground="#F8FAFC",
            font=("Segoe UI", 22, "bold")
        )
        style.configure(
            "Subtitle.TLabel", background="#101827", foreground="#A9B7CC",
            font=("Segoe UI", 10)
        )
        style.configure(
            "CardTitle.TLabel", background="#182438", foreground="#F8FAFC",
            font=("Segoe UI", 12, "bold")
        )
        style.configure(
            "CardText.TLabel", background="#182438", foreground="#B9C5D6",
            font=("Segoe UI", 10)
        )
        style.configure(
            "Value.TLabel", background="#182438", foreground="#55D6BE",
            font=("Segoe UI", 28, "bold")
        )
        style.configure(
            "Status.TLabel", background="#182438", foreground="#B9C5D6",
            font=("Segoe UI", 9)
        )
        style.configure(
            "Accent.TButton", background="#3478F6", foreground="white",
            borderwidth=0, padding=(16, 9), font=("Segoe UI", 10, "bold")
        )
        style.map("Accent.TButton", background=[("active", "#2864D2")])
        style.configure(
            "Support.TButton", background="#101827", foreground="#55D6BE",
            borderwidth=0, padding=(10, 6), font=("Segoe UI", 9)
        )
        style.map(
            "Support.TButton",
            background=[("active", "#182438")],
            foreground=[("active", "#F8FAFC")],
        )
        style.configure(
            "SoundUp.Horizontal.TScale", troughcolor="#2A3A54",
            background="#55D6BE", borderwidth=0, sliderlength=22
        )

    def _build_ui(self) -> None:
        frame = ttk.Frame(self, padding=24, style="Window.TFrame")
        frame.grid()
        header = ttk.Frame(frame, style="Window.TFrame")
        header.grid(row=0, column=0, rowspan=2, sticky="w", pady=(0, 18))
        self._header_logo = self._load_header_logo()
        if self._header_logo is not None:
            ttk.Label(header, image=self._header_logo).grid(
                row=0, column=0, rowspan=2, padx=(0, 12)
            )
        ttk.Label(header, text="SoundUp", style="Title.TLabel").grid(
            row=0, column=1, sticky="w"
        )
        ttk.Label(
            header, text="Pré-amplificador simples para seu headset",
            style="Subtitle.TLabel"
        ).grid(row=1, column=1, sticky="w", pady=(2, 0))

        ttk.Label(frame, text="Saída de áudio", style="Subtitle.TLabel").grid(
            row=2, column=0, sticky="w"
        )
        self.device_var = tk.StringVar(value=self.selected_device.FriendlyName)
        device_menu = ttk.Combobox(
            frame, textvariable=self.device_var,
            values=list(self.device_by_name), state="readonly", width=43
        )
        device_menu.grid(row=3, column=0, sticky="ew", pady=(5, 16))
        device_menu.bind("<<ComboboxSelected>>", self._on_device_selected)

        card = ttk.Frame(frame, padding=20, style="Card.TFrame")
        card.grid(row=4, column=0, sticky="ew")
        ttk.Label(card, text="Ganho de saída", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            card, text="Ajuste o volume sem alterar EQ, Hz ou DTS.",
            style="CardText.TLabel"
        ).grid(row=1, column=0, sticky="w", pady=(4, 16))
        self.value_label = ttk.Label(
            card, text=f"{self.gain.get()}%", style="Value.TLabel"
        )
        self.value_label.grid(row=2, column=0, pady=(0, 10))
        ttk.Label(card, text="100%", style="CardText.TLabel").grid(
            row=3, column=0, sticky="w"
        )
        self.scale = ttk.Scale(
            card, from_=MIN_GAIN, to=MAX_GAIN, orient="horizontal",
            command=self._on_slider, length=320, style="SoundUp.Horizontal.TScale"
        )
        self.scale.set(self.gain.get())
        self.scale.grid(row=4, column=0, pady=(3, 0))
        ttk.Label(card, text="300%", style="CardText.TLabel").grid(
            row=5, column=0, sticky="e"
        )
        ttk.Label(
            card, text="Atalho global: Ctrl+Alt+↑/↓",
            style="CardText.TLabel"
        ).grid(row=6, column=0, sticky="w", pady=(8, 0))
        ttk.Label(
            card, textvariable=self.status, wraplength=320, justify="left",
            style="Status.TLabel"
        ).grid(row=7, column=0, sticky="w", pady=(14, 0))
        ttk.Label(
            frame, text="Proteção contra clipping incluída no ganho adicional.",
            style="Subtitle.TLabel"
        ).grid(row=5, column=0, pady=(14, 12), sticky="w")
        ttk.Button(
            frame, text="Restaurar padrão", command=self._reset,
            style="Accent.TButton"
        ).grid(row=6, column=0, sticky="ew")
        ttk.Button(
            frame, text="Configurar saída no Equalizer APO",
            command=self._show_setup_dialog,
        ).grid(row=7, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(
            frame, text="♥ Apoie o projeto",
            command=self._show_support_dialog,
            style="Support.TButton",
        ).grid(row=8, column=0, pady=(12, 0))

    def _show_support_dialog(self) -> None:
        """Show the Pix donation QR code bundled with the application."""
        image_path = resource_path("qrcodeapoio.png")
        if not image_path.is_file():
            messagebox.showerror(
                "Apoie o projeto",
                f"Imagem do QR Code não encontrada:\n{image_path}",
            )
            return

        dialog = tk.Toplevel(self)
        dialog.title("Apoie o projeto")
        dialog.configure(bg="#101827")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=22, style="Window.TFrame")
        frame.grid()
        ttk.Label(frame, text="Apoie o projeto", style="Title.TLabel").grid(
            row=0, column=0
        )
        ttk.Label(
            frame,
            text=(
                "Escaneie o QR Code com o aplicativo do seu banco para "
                "fazer uma doação via Pix."
            ),
            wraplength=360,
            justify="center",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, pady=(8, 16))

        try:
            with Image.open(image_path) as source:
                qr_image = source.convert("RGB").resize((320, 320), Image.LANCZOS)
            qr_photo = ImageTk.PhotoImage(qr_image)
        except (OSError, ValueError) as error:
            dialog.destroy()
            messagebox.showerror(
                "Apoie o projeto",
                f"Não foi possível carregar o QR Code:\n{error}",
            )
            return

        # Keep a reference so Tkinter does not garbage-collect the image.
        dialog.qr_photo = qr_photo
        qr_frame = tk.Frame(frame, bg="white", padx=8, pady=8)
        qr_frame.grid(row=2, column=0)
        tk.Label(qr_frame, image=qr_photo, bg="white", borderwidth=0).pack()

        ttk.Label(
            frame, text="Obrigado pelo apoio! ♥", style="Subtitle.TLabel"
        ).grid(row=3, column=0, pady=(14, 12))
        ttk.Button(
            frame, text="Fechar", command=dialog.destroy, style="Accent.TButton"
        ).grid(row=4, column=0, sticky="ew")
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

    def _on_device_selected(self, _event=None) -> None:
        selected = self.device_by_name.get(self.device_var.get())
        if selected is None or selected.id == self.selected_device.id:
            return
        self.selected_device = selected
        self.endpoint = endpoint_volume(selected)
        self.gain.set(100)
        self.scale.set(100)
        self._cancel_pending_gain()
        self.value_label.configure(text="100%")
        self._save_device_id()
        try:
            self.apo.set_gain(100)
            self._save_gain_now(100)
            self.status.set(
                f"Dispositivo selecionado: {selected.FriendlyName}. "
                "Ganho restaurado para 100%. "
                "Marque-o no Configurator do Equalizer APO."
            )
        except (OSError, RuntimeError) as error:
            self.status.set(
                "Dispositivo selecionado, mas não foi possível restaurar o ganho: "
                f"{self._friendly_error(error)}"
            )
        self._update_status()

    def _apply_window_icon(self) -> None:
        icon = resource_path("soundup.ico")
        if not icon.is_file():
            return
        try:
            self.iconbitmap(default=str(icon))
        except tk.TclError:
            pass

    @staticmethod
    def _load_header_logo() -> ImageTk.PhotoImage | None:
        """Load the official artwork for the in-app header."""
        icon = resource_path("soundup.ico")
        if not icon.is_file():
            return None
        try:
            with Image.open(icon) as image:
                logo = image.convert("RGBA").resize((64, 64), Image.LANCZOS)
            return ImageTk.PhotoImage(logo)
        except (OSError, tk.TclError):
            return None

    @staticmethod
    def _tray_image() -> Image.Image:
        """Return the SoundUp icon used in the Windows notification area."""
        icon = resource_path("soundup.ico")
        if icon.is_file():
            try:
                with Image.open(icon) as image:
                    return image.convert("RGBA").resize((64, 64), Image.LANCZOS)
            except OSError:
                pass
        image = Image.new("RGBA", (64, 64), "#101827")
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((5, 5, 59, 59), radius=14, fill="#182438")
        draw.polygon(((16, 29), (26, 29), (37, 18), (37, 46), (26, 35), (16, 35)), fill="#55D6BE")
        draw.arc((27, 19, 50, 45), start=300, end=60, fill="#F8FAFC", width=4)
        draw.arc((32, 13, 57, 51), start=305, end=55, fill="#A9B7CC", width=3)
        return image

    def _on_window_configure(self, _event=None) -> None:
        if not self._closing and self.state() == "iconic":
            self.after_idle(self._hide_to_tray)

    def _hide_to_tray(self) -> None:
        if self._closing or self.state() != "iconic":
            return
        self._ensure_tray_icon()
        self.withdraw()
        if self._tray_icon is not None:
            self._tray_icon.visible = True

    def _ensure_tray_icon(self) -> None:
        if self._tray_icon is not None:
            return
        self._tray_icon = pystray.Icon(
            "SoundUp",
            self._tray_image(),
            "SoundUp — amplificador de áudio",
            menu=pystray.Menu(
                pystray.MenuItem("Abrir SoundUp", self._queue_restore, default=True),
                pystray.MenuItem("Sair", self._queue_close),
            ),
        )
        self._tray_icon.run_detached()

    def _queue_restore(self, _icon=None, _item=None) -> None:
        self._tray_actions.put("restore")

    def _queue_close(self, _icon=None, _item=None) -> None:
        self._tray_actions.put("close")

    def _process_tray_actions(self) -> None:
        if self._closing:
            return
        try:
            while True:
                action = self._tray_actions.get_nowait()
                if action == "restore":
                    self._restore_from_tray()
                elif action == "close":
                    self._close()
                    return
        except Empty:
            pass
        self.after(100, self._process_tray_actions)

    def _restore_from_tray(self) -> None:
        if self._tray_icon is not None:
            self._tray_icon.visible = False
        self.deiconify()
        self.lift()
        self.focus_force()

    @staticmethod
    def _clamp_gain(value: int) -> int:
        return max(MIN_GAIN, min(MAX_GAIN, int(value)))

    def _on_slider(self, value: str) -> None:
        if self._suppress_slider:
            return
        gain = self._clamp_gain(round(float(value)))
        self.gain.set(gain)
        self.value_label.configure(text=f"{gain}%")
        # Debounce disk writes: ttk.Scale fires on every pixel while dragging.
        self._cancel_pending_gain()
        self._gain_apply_job = self.after(150, lambda: self._apply_gain(gain))

    def _set_gain(self, gain: int, apply_immediately: bool = False) -> None:
        """Update the slider and schedule (or apply) the new gain."""
        gain = self._clamp_gain(gain)
        self.gain.set(gain)
        self.value_label.configure(text=f"{gain}%")
        self._suppress_slider = True
        try:
            self.scale.set(gain)
        finally:
            self._suppress_slider = False
        self._cancel_pending_gain()
        if apply_immediately:
            self._apply_gain(gain)
        else:
            self._gain_apply_job = self.after(150, lambda: self._apply_gain(gain))

    def _apply_gain(self, gain: int) -> None:
        self._gain_apply_job = None
        try:
            self.apo.set_gain(gain)
            self._schedule_save_gain(gain)
            self._update_status()
        except (OSError, RuntimeError) as error:
            self.status.set(self._friendly_error(error))

    def _cancel_pending_gain(self) -> None:
        if self._gain_apply_job is not None:
            self.after_cancel(self._gain_apply_job)
            self._gain_apply_job = None

    @staticmethod
    def _modifiers_down() -> bool:
        ctrl = any(
            key_is_down(vk) for vk in (VK_CONTROL, VK_LCONTROL, VK_RCONTROL)
        )
        alt = any(key_is_down(vk) for vk in (VK_MENU, VK_LMENU, VK_RMENU))
        return ctrl and alt

    def _poll_hotkeys(self) -> None:
        """Ctrl+Alt+Up/Down works globally, even with the window in the tray."""
        if self._closing:
            return
        try:
            modifiers = self._modifiers_down()
            up = modifiers and key_is_down(VK_UP)
            down = modifiers and key_is_down(VK_DOWN)
            direction = 1 if up and not down else -1 if down and not up else 0
            now = time.monotonic()
            if direction != self._hotkey_direction:
                self._hotkey_direction = direction
                if direction != 0:
                    self._hotkey_started_at = now
                    self._hotkey_next_repeat_at = now + HOTKEY_HOLD_DELAY
                    self._step_hotkey(direction)
                else:
                    self._hotkey_started_at = 0.0
            elif direction != 0 and now >= self._hotkey_next_repeat_at:
                self._step_hotkey(direction)
                held = now - self._hotkey_started_at
                if held < HOTKEY_RAMP_THRESHOLDS[0]:
                    interval = HOTKEY_RAMP_INTERVALS[0]
                elif held < HOTKEY_RAMP_THRESHOLDS[1]:
                    interval = HOTKEY_RAMP_INTERVALS[1]
                else:
                    interval = HOTKEY_RAMP_INTERVALS[2]
                self._hotkey_next_repeat_at = now + interval
        finally:
            if not self._closing:
                self.after(HOTKEY_POLL_MS, self._poll_hotkeys)

    def _step_hotkey(self, direction: int) -> None:
        current = self.gain.get()
        target = self._clamp_gain(current + direction * GAIN_STEP)
        if target != current:
            self._set_gain(target, apply_immediately=True)
        self._show_gain_overlay()

    def _build_overlay(self) -> None:
        overlay = tk.Toplevel(self)
        overlay.withdraw()
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True)
        overlay.attributes("-alpha", 0.0)
        overlay.configure(bg="#0B1220")
        frame = tk.Frame(
            overlay, bg="#182438", padx=18, pady=12,
            highlightbackground="#3478F6", highlightthickness=1,
        )
        frame.pack()
        header = tk.Frame(frame, bg="#182438")
        header.pack(fill="x")
        tk.Label(
            header, text="SoundUp", bg="#182438", fg="#A9B7CC",
            font=("Segoe UI", 9),
        ).pack(side="left")
        self._overlay_value = tk.Label(
            header, text=f"{self.gain.get()}%", bg="#182438", fg="#55D6BE",
            font=("Segoe UI", 18, "bold"),
        )
        self._overlay_value.pack(side="right")
        self._overlay_canvas = tk.Canvas(
            frame, width=200, height=8, bg="#2A3A54",
            highlightthickness=0,
        )
        self._overlay_canvas.pack(pady=(10, 0))
        self._overlay_bar = self._overlay_canvas.create_rectangle(
            0, 0, 0, 8, fill="#55D6BE", outline=""
        )
        self._overlay = overlay
        overlay.update_idletasks()
        self._apply_overlay_ex_styles()

    def _apply_overlay_ex_styles(self) -> None:
        if self._overlay is None:
            return
        try:
            hwnd = self._overlay.winfo_id()
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            )
        except (AttributeError, OSError, tk.TclError):
            pass

    def _update_overlay(self) -> None:
        if self._overlay is None:
            return
        gain = self.gain.get()
        self._overlay_value.configure(text=f"{gain}%")
        ratio = (gain - MIN_GAIN) / (MAX_GAIN - MIN_GAIN)
        width = max(2, int(200 * ratio))
        self._overlay_canvas.coords(self._overlay_bar, 0, 0, width, 8)

    def _position_overlay(self) -> None:
        if self._overlay is None:
            return
        self._overlay.update_idletasks()
        width = max(180, self._overlay.winfo_reqwidth())
        height = max(60, self._overlay.winfo_reqheight())
        x = y = None
        try:
            point = _Point()
            user32 = ctypes.windll.user32
            if user32.GetCursorPos(ctypes.byref(point)):
                monitor = user32.MonitorFromPoint(point, 2)
                info = _MonitorInfo()
                info.cbSize = ctypes.sizeof(_MonitorInfo)
                if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                    work = info.rcWork
                    x = work.left + (work.right - work.left - width) // 2
                    y = work.bottom - height - 80
        except (AttributeError, OSError, tk.TclError):
            pass
        if x is None or y is None:
            x = (self.winfo_screenwidth() - width) // 2
            y = self.winfo_screenheight() - height - 120
        self._overlay.geometry(f"{width}x{height}+{x}+{y}")

    def _show_gain_overlay(self) -> None:
        if self._closing:
            return
        if self._overlay is None:
            self._build_overlay()
        if self._overlay is None:
            return
        was_hidden = self._overlay.state() == "withdrawn"
        self._update_overlay()
        self._overlay.attributes("-alpha", 0.94)
        if was_hidden:
            self._position_overlay()
            self._overlay.deiconify()
            self._overlay.lift()
            self._overlay.attributes("-topmost", True)
            self._apply_overlay_ex_styles()
            try:
                hwnd = self._overlay.winfo_id()
                user32 = ctypes.windll.user32
                user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
                user32.SetWindowPos(
                    hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
                )
            except (AttributeError, OSError, tk.TclError):
                pass
        if self._overlay_job is not None:
            self.after_cancel(self._overlay_job)
            self._overlay_job = None
        self._overlay_job = self.after(2000, lambda: self._fade_overlay(0.94))

    def _fade_overlay(self, alpha: float) -> None:
        self._overlay_job = None
        if self._closing or self._overlay is None:
            return
        alpha -= 0.12
        if alpha <= 0.02:
            self._overlay.attributes("-alpha", 0.0)
            self._overlay.withdraw()
        else:
            self._overlay.attributes("-alpha", alpha)
            self._overlay_job = self.after(30, lambda: self._fade_overlay(alpha))

    @staticmethod
    def _friendly_error(error: Exception) -> str:
        if isinstance(error, PermissionError) or getattr(error, "winerror", None) == 5:
            return (
                "Sem permissão para alterar a configuração do Equalizer APO. "
                "Reinstale o SoundUp ou execute-o como administrador uma vez."
            )
        return str(error)

    def _update_status(self) -> None:
        if not self.status.get():
            self.status.set("Equalizer APO ativo: controle direto de ganho.")

    def _reset(self) -> None:
        self.gain.set(MIN_GAIN)
        self._suppress_slider = True
        try:
            self.scale.set(MIN_GAIN)
        finally:
            self._suppress_slider = False
        self._cancel_pending_gain()
        self.value_label.configure(text=f"{MIN_GAIN}%")
        try:
            self.apo.set_gain(MIN_GAIN)
            self._save_gain_now(MIN_GAIN)
            self._update_status()
        except (OSError, RuntimeError) as error:
            messagebox.showerror(
                "Não foi possível restaurar", self._friendly_error(error)
            )

    def _close(self) -> None:
        self._closing = True
        self._cancel_pending_gain()
        if self._save_gain_job is not None:
            self.after_cancel(self._save_gain_job)
            self._save_gain_job = None
        self._save_gain_now(self.gain.get())
        if self._overlay_job is not None:
            self.after_cancel(self._overlay_job)
            self._overlay_job = None
        if self._tray_icon is not None:
            self._tray_icon.stop()
        self.destroy()


def main() -> None:
    try:
        app = SoundUpApp()
    except ApoNotInstalledError as error:
        messagebox.showerror(
            "Equalizer APO não encontrado",
            "O SoundUp precisa do Equalizer APO para funcionar, mas ele não foi "
            "encontrado.\n\n"
            "Execute o instalador do SoundUp novamente e aceite a instalação do "
            "Equalizer APO.\n\n"
            f"Detalhes: {error}",
        )
        return
    except NoAudioOutputError as error:
        messagebox.showerror(
            "Nenhuma saída de áudio encontrada",
            "Conecte ou ative um dispositivo de saída de áudio e abra o SoundUp "
            "novamente.\n\n"
            f"Detalhes: {error}",
        )
        return
    except PermissionError as error:
        messagebox.showerror(
            "Permissão necessária",
            "O SoundUp não tem permissão para alterar a configuração do "
            "Equalizer APO.\n\n"
            "Reinstale o SoundUp ou execute-o como administrador uma vez para "
            "concluir a configuração.\n\n"
            f"Detalhes: {error}",
        )
        return
    except Exception as error:
        messagebox.showerror(
            "SoundUp",
            "Não foi possível iniciar o SoundUp.\n\n"
            f"Detalhes: {error}",
        )
        return
    if app.startup_cancelled:
        return
    app.mainloop()


if __name__ == "__main__":
    main()
