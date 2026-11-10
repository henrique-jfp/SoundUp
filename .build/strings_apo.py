import re
from pathlib import Path

path = Path(r"C:\Program Files\EqualizerAPO\EqualizerAPO.dll")
data = path.read_bytes()

# Extract ASCII and UTF-16LE strings.
patterns = [rb"[\x20-\x7e]{4,}"]
utf16 = re.findall(rb"(?:[\x20-\x7e]\x00){4,}", data)
ascii_strings = [s.decode("ascii", "ignore") for s in re.findall(rb"[\x20-\x7e]{4,}", data)]
unicode_strings = [s.decode("utf-16le", "ignore") for s in utf16]

keywords = ("trace", "log", "config", "registry", "software\\", "hklm", "hkcu", "equalizerapo")
for text in sorted(set(ascii_strings + unicode_strings)):
    low = text.lower()
    if any(keyword in low for keyword in keywords) and len(text) < 250:
        print(text)
