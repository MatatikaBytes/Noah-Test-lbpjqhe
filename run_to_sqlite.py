"""Run tap-dogapi via meltano and load results into a SQLite database."""
import json
import sqlite3
import subprocess
import sys

DB_PATH = sys.argv[1]

SINGER_TO_SQL = {
    "integer": "INTEGER",
    "number":  "REAL",
    "boolean": "INTEGER",
    "string":  "TEXT",
    "object":  "TEXT",
    "array":   "TEXT",
}

proc = subprocess.Popen(
    ["meltano", "invoke", "tap-dogapi"],
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL,
    text=True,
    encoding="utf-8",
)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
record_count = 0

for line in proc.stdout:
    line = line.strip()
    if not line or not line.startswith("{"):
        continue
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        continue

    msg_type = msg.get("type")

    if msg_type == "SCHEMA":
        stream = msg["stream"]
        props = msg["schema"].get("properties", {})
        cols = []
        for col, spec in props.items():
            t = spec.get("type", "string")
            if isinstance(t, list):
                t = next((x for x in t if x != "null"), "string")
            cols.append(f'"{col}" {SINGER_TO_SQL.get(t, "TEXT")}')
        cur.execute(f'DROP TABLE IF EXISTS "{stream}"')
        cur.execute(f'CREATE TABLE "{stream}" ({", ".join(cols)})')
        conn.commit()
        print(f"Created table: {stream}")

    elif msg_type == "RECORD":
        stream = msg["stream"]
        record = msg["record"]
        cols = list(record.keys())
        vals = [int(v) if isinstance(v, bool) else v for v in (record[c] for c in cols)]
        placeholders = ", ".join("?" for _ in cols)
        col_list = ", ".join(f'"{c}"' for c in cols)
        cur.execute(f'INSERT INTO "{stream}" ({col_list}) VALUES ({placeholders})', vals)
        record_count += 1

proc.wait()
conn.commit()
conn.close()
print(f"Done: {record_count} records written to {DB_PATH}")
