"""Ensure corrupted CRLF line endings are repaired and never rewritten twice."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "legacy"))
import soundup_preamp as soundup  # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    config = root / "config.txt"
    include = root / "soundup-preamp.txt"
    soundup.APO_CONFIG = config
    soundup.APO_INCLUDE = include
    soundup.APO_INCLUDE_LINE = f"Include: {include}"

    config.write_bytes(
        b"Preamp: -6 dB\r\r\n"
        b"\r\r\n"
        b"Include: example.txt\r\r\n"
        b"\r\r\n"
        b"Include: soundup-preamp.txt\r\r\n"
    )
    controller = soundup.EqualizerApoController()
    raw = config.read_bytes()
    assert b"\r\r\n" not in raw, raw
    assert b"Include: example.txt\r\n" in raw, raw
    assert f"Include: {include}".encode() in raw, raw
    assert raw.count(b"soundup-preamp.txt") == 1, raw
    assert controller.repaired_include is True

    controller.set_gain(300)
    after = config.read_bytes()
    assert after == raw, (after, raw)
    assert b"\r\r\n" not in after, after
    assert b"+9.54 dB" in include.read_bytes(), include.read_bytes()

    # A healthy LF file keeps LF and is not rewritten needlessly.
    config.write_bytes(b"Preamp: -6 dB\nInclude: example.txt\n")
    controller = soundup.EqualizerApoController()
    raw = config.read_bytes()
    assert b"\r" not in raw, raw
    assert raw.endswith(f"Include: {include}".encode() + b"\n"), raw

print("OK: quebras de linha normalizadas, sem duplicar CR e sem duplicatas")
