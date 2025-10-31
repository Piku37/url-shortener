from pathlib import Path
import sqlite3

sql = """
CREATE TABLE IF NOT EXISTS url (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  original_url TEXT NOT NULL,
  short_code VARCHAR(10) UNIQUE NOT NULL,
  clicks INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT (datetime('now'))
);
"""

for p in ("urls.db", "data/urls.db"):
    path = Path(p)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(f"{p} -> tables: {tables}")
    conn.close()
