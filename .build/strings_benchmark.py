import re
from pathlib import Path

path = Path(r"C:\Program Files\EqualizerAPO\Benchmark.exe")
data = path.read_bytes()
ascii_strings = re.findall(rb"[\x20-\x7e]{4,}", data)
keywords = ("usage", "config", "Usage", "option", "argument", "filter", "output", "input", "benchmark")
seen = set()
for item in ascii_strings:
    text = item.decode("ascii", "ignore")
    low = text.lower()
    if any(keyword.lower() in low for keyword in keywords):
        if text not in seen and len(text) < 200:
            seen.add(text)
            print(text)
