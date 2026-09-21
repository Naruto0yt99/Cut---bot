import sqlite3, time
from pathlib import Path

class StickerStore:
    def __init__(self,db_url="bot_memory.db"):
        self.path=Path(db_url.replace("sqlite:///",""))
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS stickers(
                id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, pack_name TEXT,
                file_id TEXT, file_unique_id TEXT, emoji TEXT, safe INTEGER DEFAULT 1,
                created_at REAL)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_sticker_pack ON stickers(pack_name)")
            c.execute("""CREATE TABLE IF NOT EXISTS sticker_usage(
                file_unique_id TEXT PRIMARY KEY, uses INTEGER DEFAULT 0, last_used REAL DEFAULT 0)""")

    def add(self,chat_id,pack_name,file_id,file_unique_id,emoji,safe=1):
        with sqlite3.connect(self.path) as c:
            c.execute("""INSERT INTO stickers(chat_id,pack_name,file_id,file_unique_id,emoji,safe,created_at)
                         VALUES(?,?,?,?,?,?,?)""",
                      (chat_id,pack_name or "",file_id,file_unique_id,emoji or "",int(bool(safe)),time.time()))

    def mark_used(self,file_unique_id):
        with sqlite3.connect(self.path) as c:
            c.execute("""INSERT INTO sticker_usage(file_unique_id,uses,last_used) VALUES(?,?,?)
                         ON CONFLICT(file_unique_id) DO UPDATE SET uses=uses+1,last_used=excluded.last_used""",
                      (file_unique_id,1,time.time()))

    def candidates(self,chat_id,emoji=None,limit=12):
        with sqlite3.connect(self.path) as c:
            if emoji:
                return c.execute("""SELECT file_id,file_unique_id,pack_name,emoji FROM stickers
                    WHERE chat_id=? AND safe=1 AND emoji=? ORDER BY RANDOM() LIMIT ?""",(chat_id,emoji,limit)).fetchall()
            return c.execute("""SELECT file_id,file_unique_id,pack_name,emoji FROM stickers
                    WHERE chat_id=? AND safe=1 ORDER BY RANDOM() LIMIT ?""",(chat_id,limit)).fetchall()
