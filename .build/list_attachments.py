import json
import sqlite3

DB = r"C:\Users\henri\.local\share\opencode\opencode.db"
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cur = con.cursor()
rows = cur.execute(
    "SELECT id, session_id, type, seq, time_created, time_updated, data "
    "FROM session_message ORDER BY time_updated DESC LIMIT 40"
).fetchall()
for row in rows:
    msg_id, session_id, msg_type, seq, created, updated, data = row
    try:
        payload = json.loads(data)
    except Exception:
        payload = data
    files = None
    if isinstance(payload, dict):
        files = payload.get("files")
        if files is None and isinstance(payload.get("data"), dict):
            files = payload["data"].get("files")
    info = ""
    if files:
        info = f" files={[(f.get('name') or f.get('filename'), f.get('mime'), len(f.get('data',''))) for f in files]}"
    print(msg_id, msg_type, seq, updated, "len=", len(data), info)
con.close()
