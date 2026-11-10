import base64
import json
import sqlite3
from pathlib import Path

DB = r"C:\Users\henri\.local\share\opencode\opencode.db"
MSG = "msg_1b851f97c001LcvQdM36yBMEFJ"
OUT = Path(__file__).resolve().parent / "new_logo_source.png"

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
row = con.execute(
    "SELECT data FROM session_message WHERE id = ?", (MSG,)
).fetchone()
con.close()
payload = json.loads(row[0])
file_info = payload["files"][0]
data = file_info["data"]
if "," in data[:100] and data.startswith("data:"):
    data = data.split(",", 1)[1]
OUT.write_bytes(base64.b64decode(data))
print("salvo:", OUT, OUT.stat().st_size, "bytes")
print("nome:", file_info.get("name"), "mime:", file_info.get("mime"))

from PIL import Image

with Image.open(OUT) as image:
    print("formato:", image.format, "tamanho:", image.size, "modo:", image.mode)
