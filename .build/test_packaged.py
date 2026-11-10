"""Smoke-test the packaged 2.0.6.0 EXE with simulated global hotkeys."""
import ctypes
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXE = ROOT / "legacy" / "dist" / "SoundUp.exe"
SETTINGS = Path(os.environ["LOCALAPPDATA"]) / "SoundUp"
GAIN_FILE = SETTINGS / "gain.txt"

subprocess.run(
    ["taskkill", "/IM", "SoundUp.exe", "/F"], capture_output=True, check=False
)
time.sleep(1)
SETTINGS.mkdir(parents=True, exist_ok=True)
GAIN_FILE.write_text("100", encoding="utf-8")

proc = subprocess.Popen([str(EXE)])
time.sleep(7)
user32 = ctypes.windll.user32


def tap() -> None:
    user32.keybd_event(0x11, 0, 0, 0)
    user32.keybd_event(0x12, 0, 0, 0)
    user32.keybd_event(0x26, 0, 0, 0)
    time.sleep(0.08)
    user32.keybd_event(0x26, 0, 2, 0)
    user32.keybd_event(0x12, 0, 2, 0)
    user32.keybd_event(0x11, 0, 2, 0)


print("rodando:", proc.poll() is None)
tap()
time.sleep(1.0)
print("apos toque:", GAIN_FILE.read_text(encoding="utf-8"))

user32.keybd_event(0x11, 0, 0, 0)
user32.keybd_event(0x12, 0, 0, 0)
user32.keybd_event(0x26, 0, 0, 0)
time.sleep(1.5)
user32.keybd_event(0x26, 0, 2, 0)
user32.keybd_event(0x12, 0, 2, 0)
user32.keybd_event(0x11, 0, 2, 0)
time.sleep(1.0)
print("apos segurar:", GAIN_FILE.read_text(encoding="utf-8"))

subprocess.run(
    ["taskkill", "/IM", "SoundUp.exe", "/F"], capture_output=True, check=False
)
time.sleep(1)

sys.path.insert(0, str(ROOT / "legacy"))
import soundup_preamp as soundup  # noqa: E402

soundup.EqualizerApoController().set_gain(soundup.MIN_GAIN)
GAIN_FILE.write_text("100", encoding="utf-8")
print("restaurado para 100%")
