"""Exercise tap, hold ramp, limits, overlay auto-hide, focus and persistence."""
import ctypes
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "legacy"))
import soundup_preamp as soundup  # noqa: E402

TEMP_GAIN = ROOT / ".build" / "test_gain.txt"
TEMP_GAIN.write_text("175", encoding="utf-8")
soundup.GAIN_FILE = TEMP_GAIN

app = soundup.SoundUpApp()
app.withdraw()
user32 = ctypes.windll.user32
results = {}


def keys(down_vk: int, hold: float) -> None:
    user32.keybd_event(0x11, 0, 0, 0)
    user32.keybd_event(0x12, 0, 0, 0)
    user32.keybd_event(down_vk, 0, 0, 0)
    time.sleep(hold)
    user32.keybd_event(down_vk, 0, 2, 0)
    user32.keybd_event(0x12, 0, 2, 0)
    user32.keybd_event(0x11, 0, 2, 0)


def start_keys(down_vk: int, hold: float) -> None:
    threading.Thread(target=keys, args=(down_vk, hold), daemon=True).start()


def snap(label: str) -> None:
    results[label] = {
        "gain": app.gain.get(),
        "scale": round(app.scale.get()),
        "overlay": app._overlay.state() if app._overlay else None,
        "foreground": user32.GetForegroundWindow(),
    }


def finish() -> None:
    results["saved_file_before_close"] = TEMP_GAIN.read_text(encoding="utf-8")
    app._set_gain(175, apply_immediately=True)
    app.after(200, close)


def close() -> None:
    app._close()
    results["saved_file_after_close"] = TEMP_GAIN.read_text(encoding="utf-8")
    results["load_gain"] = soundup.SoundUpApp._load_gain()
    soundup.EqualizerApoController().set_gain(soundup.MIN_GAIN)
    print(results)


# Startup restored 175 from the gain file.
app.after(200, lambda: results.setdefault(
    "foreground_baseline", user32.GetForegroundWindow()
))
app.after(300, lambda: snap("startup_restored"))
app.after(500, lambda: app._set_gain(100, apply_immediately=True))
# Quick tap: exactly one 5% step.
app.after(800, lambda: start_keys(0x26, 0.06))
app.after(1600, lambda: snap("after_tap"))
app.after(3600, lambda: snap("after_overlay_timeout"))
# Upper limit: holding up at 300% must not exceed it.
app.after(3800, lambda: app._set_gain(300, apply_immediately=True))
app.after(4000, lambda: start_keys(0x26, 0.9))
app.after(5300, lambda: snap("limit_max"))
# Lower limit: holding down at 100% must not go below it.
app.after(5500, lambda: app._set_gain(100, apply_immediately=True))
app.after(5700, lambda: start_keys(0x28, 0.9))
app.after(7000, lambda: snap("limit_min"))
app.after(7200, finish)
app.mainloop()
