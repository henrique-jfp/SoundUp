from pathlib import Path

config = Path(r"C:\Program Files\EqualizerAPO\config\config.txt")
backup = Path(r"C:\Program Files\EqualizerAPO\config\config.txt.diag3-backup")
backup.write_bytes(config.read_bytes())
include = r"C:\Program Files\EqualizerAPO\config\soundup-preamp.txt"
config.write_bytes(
    ("Preamp: -6 dB\r\nInclude: " + include + "\r\n").encode("utf-8")
)
print("config CRLF com include absoluto gravado")
