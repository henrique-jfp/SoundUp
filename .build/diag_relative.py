from pathlib import Path

root = Path(r"C:\Projetos Pessoais\SoundUp")
config = Path(r"C:\Program Files\EqualizerAPO\config\config.txt")
backup = Path(r"C:\Program Files\EqualizerAPO\config\config.txt.diag2-backup")

root.joinpath("relative-test.txt").write_text("Preamp: +20 dB\n", encoding="utf-8")
backup.write_bytes(config.read_bytes())
config.write_text("Preamp: -6 dB\nInclude: relative-test.txt\n", encoding="utf-8")
print("config com include relativo ao CWD gravado")
