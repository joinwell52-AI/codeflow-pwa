import sqlite3, json, os

appdata = os.environ['APPDATA']
ws_dir = os.path.join(appdata, 'Cursor', 'User', 'workspaceStorage')

for ws in os.listdir(ws_dir):
    db_path = os.path.join(ws_dir, ws, 'state.vscdb')
    if not os.path.exists(db_path):
        continue
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT key FROM ItemTable WHERE key LIKE '%aichat%' OR key LIKE '%agent%'")
        rows = cur.fetchall()
        if rows:
            print(f"=== {ws} ===")
            for r in rows:
                print(f"  key: {r[0]}")
                cur2 = conn.cursor()
                cur2.execute("SELECT value FROM ItemTable WHERE key=?", (r[0],))
                val = cur2.fetchone()
                if val:
                    v = val[0][:800] if len(val[0]) > 800 else val[0]
                    print(f"  val: {v}")
        conn.close()
    except Exception as e:
        print(f"Error {ws}: {e}")
