from pathlib import Path

config = Path(r"C:\Program Files\EqualizerAPO\config\config.txt")
text = config.read_text(encoding="utf-8-sig")
lines = [
    line for line in text.splitlines()
    if "soundup-preamp.txt" not in line
]
lines.append(
    "Include: C:\\Program Files\\EqualizerAPO\\config\\soundup-preamp.txt"
)
config.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(config.read_text(encoding="utf-8-sig"))
