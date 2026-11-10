from pathlib import Path

config = Path(r"C:\Program Files\EqualizerAPO\config\config.txt")
backup = Path(r"C:\Program Files\EqualizerAPO\config\config.txt.diag6-backup")
backup.write_bytes(config.read_bytes())

text = (
    "Preamp: -6 dB\n"
    "\n"
    "Include: example.txt\n"
    "\n"
    "GraphicEQ: 25 0; 40 0; 63 0; 100 0; 160 0; 250 0; 400 0; 630 0; 1000 0; "
    "1600 0; 2500 0; 4000 0; 6300 0; 10000 0; 16000 0\n"
    "\n"
    "Include: soundup-preamp.txt\n"
    "\n"
)
config.write_bytes(text.encode("utf-8"))
print(repr(text))
