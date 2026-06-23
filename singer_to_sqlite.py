"""Reads Singer-protocol messages from stdin and writes them to a SQLite database."""
import json
import sqlite3
import sys

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else "output.db"

SINGER_TO_SQL = {
    "integer": "INTEGER",
    "number":  "REAL",
    "boolean": "INTEGER",
    "string":  "TEXT",
    "object":  "TEXT",
    "array":   "TEXT",
}

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
schemas = {}

for raw in sys.stdin:
    raw = raw.strip()
    if not raw or not raw.startswith("{"):
        continue
    try:
        msg = json.loads(raw)
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
        schemas[stream] = list(props.keys())
        conn.commit()

    elif msg_type == "RECORD":
        stream = msg["stream"]
        record = msg["record"]
        cols = list(record.keys())
        vals = [
            int(v) if isinstance(v, bool) else v
            for v in (record[c] for c in cols)
        ]
        placeholders = ", ".join("?" for _ in cols)
        col_list = ", ".join(f'"{c}"' for c in cols)
        cur.execute(
            f'INSERT INTO "{stream}" ({col_list}) VALUES ({placeholders})',
            vals,
        )

conn.commit()
conn.close()
print(f"Written to {DB_PATH}", file=sys.stderr)
