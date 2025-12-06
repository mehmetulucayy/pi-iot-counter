import sqlite3, os

SCHEMA = '''
CREATE TABLE IF NOT EXISTS counts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  track_id INTEGER NOT NULL,
  direction TEXT NOT NULL CHECK(direction in ('up','down'))
);
'''

class SQLiteLogger:
    def __init__(self, db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cur = self.conn.cursor()
    def init_schema(self):
        self.cur.executescript(SCHEMA); self.conn.commit()
    def insert_count(self, ts, track_id, direction):
        self.cur.execute("INSERT INTO counts (ts, track_id, direction) VALUES (?, ?, ?)", (ts, track_id, direction))
        self.conn.commit()
    def close(self):
        self.conn.close()
