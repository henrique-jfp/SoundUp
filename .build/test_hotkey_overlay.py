"""End-to-end test: global hotkey while hidden + overlay screenshot."""
import ctypes
import sys
import threading
import time
from pathlib import Path

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "legacy"))
import soundup_preamp as soundup  # noqa: E402

TEMP_GAIN = ROOT / ".build" / "test_gain.txt"
if TEMP_GAIN.exists():
    TEMP_GAIN.unlink()
soundup.GAIN_FILE = TEMP_GAIN

app = soundup.SoundUpApp()
app.withdraw()
result = {}


def press_keys() -> None:
    user32 = ctypes.windll.user32
    user32.keybd_event(0x11, 0, 0, 0)  # Ctrl
    user32.keybd_event(0x12, 0, 0, 0)  # Alt
    user32.keybd_event(0x26, 0, 0, 0)  # Up
    time.sleep(1.2)
    user32.keybd_event(0x26, 0, 2, 0)
    user32.keybd_event(0x12, 0, 2, 0)
    user32.keybd_event(0x11, 0, 2, 0)


def capture() -> None:
    path = ROOT / ".build" / "overlay_test.png"
    ImageGrab.grab().save(path)
    result["screenshot"] = str(path)
    result["overlay_state_at_capture"] = (
        app._overlay.state() if app._overlay else None
    )


def finish() -> None:
    result["gain"] = app.gain.get()
    result["overlay_state_end"] = app._overlay.state() if app._overlay else None
    result["gain_file"] = (
        TEMP_GAIN.read_text(encoding="utf-8") if TEMP_GAIN.exists() else None
    )
    print(result)
    app._set_gain(soundup.MIN_GAIN, apply_immediately=True)
    app.after(300, app._close)


app.after(700, lambda: threading.Thread(target=press_keys, daemon=True).start())
app.after(1500, capture)
app.after(4000, finish)
app.mainloop()
