from pathlib import Path

config = Path(r"C:\Program Files\EqualizerAPO\config\config.txt")
backup = Path(r"C:\Program Files\EqualizerAPO\config\config.txt.diag5-backup")
backup.write_bytes(config.read_bytes())
config.write_bytes(b"Preamp: -6 dB\r\nInclude: soundup-preamp.txt\r\n")
print("config CRLF com include relativo gravado")
