import json
import sqlite3

DB = r"C:\Users\henri\.local\share\opencode\opencode.db"
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cur = con.cursor()
print("tables:", [row[0] for row in cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
)])
for table in ("session_message", "message", "messages"):
    try:
        cols = [row[1] for row in cur.execute(f"PRAGMA table_info({table})")]
    except sqlite3.DatabaseError:
        continue
    if cols:
        print(table, cols)
con.close()
