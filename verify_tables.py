import sqlite3, os
# try data/urls.db first, then urls.db
paths = ["data/urls.db", "urls.db"]
for p in paths:
    try:
        if not os.path.exists(p):
            print(f"{p}: NOT FOUND")
            continue
        conn = sqlite3.connect(p)
        cur = conn.cursor()
        print("DB path:", p)
        print("tables:", cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
        conn.close()
    except Exception as e:
        print(p, "ERROR", e)
