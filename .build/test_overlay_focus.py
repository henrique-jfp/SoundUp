"""Verify that showing the overlay does not steal foreground focus."""
import ctypes
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "legacy"))
import soundup_preamp as soundup  # noqa: E402

TEMP_GAIN = ROOT / ".build" / "test_gain.txt"
TEMP_GAIN.write_text("100", encoding="utf-8")
soundup.GAIN_FILE = TEMP_GAIN

app = soundup.SoundUpApp()
app.withdraw()
user32 = ctypes.windll.user32
result = {}


def before() -> None:
    result["foreground_before"] = user32.GetForegroundWindow()
    result["overlay_handle"] = app._overlay.winfo_id() if app._overlay else None
    app._step_hotkey(1)


def after() -> None:
    result["foreground_after"] = user32.GetForegroundWindow()
    result["overlay_state"] = app._overlay.state() if app._overlay else None
    result["gain"] = app.gain.get()
    print(result)
    app._set_gain(soundup.MIN_GAIN, apply_immediately=True)
    app.after(200, app._close)


app.after(700, before)
app.after(1100, after)
app.mainloop()

soundup.EqualizerApoController().set_gain(soundup.MIN_GAIN)
