from pathlib import Path

config = Path(r"C:\Program Files\EqualizerAPO\config\config.txt")
backup = Path(r"C:\Program Files\EqualizerAPO\config\config.txt.diag-backup")
include = Path(r"C:\Users\henri\AppData\Local\Temp\eqtest.txt")

include.write_text("Preamp: +20 dB\n", encoding="utf-8")
backup.write_bytes(config.read_bytes())
config.write_text(
    "Preamp: -6 dB\nInclude: C:\\Users\\henri\\AppData\\Local\\Temp\\eqtest.txt\n",
    encoding="utf-8",
)
print("config de diagnostico gravado")
