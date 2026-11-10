"""Measure the real endpoint peak at several gain values."""
import math
import struct
import sys
import time
import wave
from ctypes import POINTER, cast
from pathlib import Path

import winsound
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioMeterInformation

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "legacy"))
import soundup_preamp as soundup  # noqa: E402

WAV = Path(__file__).resolve().parent / "tone.wav"
RATE = 48000
SECONDS = 8
AMPLITUDE = 0.05

with wave.open(str(WAV), "wb") as wav:
    wav.setnchannels(2)
    wav.setsampwidth(2)
    wav.setframerate(RATE)
    frames = bytearray()
    for index in range(RATE * SECONDS):
        value = int(32767 * AMPLITUDE * math.sin(2 * math.pi * 440 * index / RATE))
        frames += struct.pack("<hh", value, value)
    wav.writeframes(frames)

device = AudioUtilities.GetSpeakers()


def meter():
    interface = device._dev.Activate(
        IAudioMeterInformation._iid_, CLSCTX_ALL, None
    )
    return cast(interface, POINTER(IAudioMeterInformation))


def measure(seconds=1.5):
    time.sleep(1.0)
    peak = 0.0
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        peak = max(peak, meter().GetPeakValue())
        time.sleep(0.02)
    return peak


original_volume = device.EndpointVolume.GetMasterVolumeLevelScalar()
device.EndpointVolume.SetMasterVolumeLevelScalar(0.5, None)
winsound.PlaySound(
    str(WAV), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP
)
try:
    controller = soundup.EqualizerApoController()
    results = {}
    for gain in (100, 200, 300, 100):
        controller.set_gain(gain)
        peak = measure()
        results.setdefault(gain, []).append(peak)
        print(f"{gain:>3}% -> pico {peak:.4f}")
finally:
    winsound.PlaySound(None, winsound.SND_PURGE)
    device.EndpointVolume.SetMasterVolumeLevelScalar(original_volume, None)

base = results[100][0]
print(f"200/100 = {results[200][0] / base:.3f} (esperado ~2.0)")
print(f"300/100 = {results[300][0] / base:.3f} (esperado ~3.0)")
print(f"100 final / 100 inicial = {results[100][1] / base:.3f} (esperado ~1.0)")
