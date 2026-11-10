"""Verify the include is always rewritten as an absolute path."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "legacy"))
import soundup_preamp as soundup

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    config = root / "config.txt"
    include = root / "soundup-preamp.txt"
    soundup.APO_CONFIG = config
    soundup.APO_INCLUDE = include
    soundup.APO_INCLUDE_LINE = f"Include: {include}"

    config.write_text(
        "Preamp: -6 dB\nInclude: soundup-preamp.txt\nInclude: outro.txt\n",
        encoding="utf-8",
    )
    controller = soundup.EqualizerApoController()
    text = config.read_text(encoding="utf-8")
    assert f"Include: {include}" in text, text
    assert "Include: soundup-preamp.txt\n" not in text.replace(
        f"Include: {include}", ""
    ), text
    assert "Include: outro.txt" in text, text
    assert controller.repaired_include is True

    controller.set_gain(300)
    text = config.read_text(encoding="utf-8")
    assert text.count("soundup-preamp.txt") == 1, text
    assert "+9.54 dB" in include.read_text(encoding="utf-8")

print("OK: include convertido para caminho absoluto e sem duplicatas")
