from pathlib import Path

config = Path(r"C:\Program Files\EqualizerAPO\config\config.txt")
backup = Path(r"C:\Program Files\EqualizerAPO\config\config.txt.diag4-backup")
backup.write_bytes(config.read_bytes())
config.write_bytes(b"Preamp: -6 dB\nInclude: soundup-preamp.txt\n")
print("config LF com include relativo gravado")
