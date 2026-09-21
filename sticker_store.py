import sqlite3, time
from pathlib import Path

class StickerStore:
    def __init__(self,db_url="bot_memory.db"):
        p=Path(db_url.replace("sqlite:///",""))
        with sqlite3.connect(p) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS stickers(
                id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, pack_name TEXT,
                file_id TEXT, file_unique_id TEXT, emoji TEXT, safe INTEGER DEFAULT 1,
                created_at REAL)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_sticker_pack ON stickers(pack_name)")

    def add(self,chat_id,pack_name,file_id,file_unique_id,emoji):
        with sqlite3.connect("bot_memory.db") as c:
            c.execute("""INSERT INTO stickers(chat_id,pack_name,file_id,file_unique_id,emoji,created_at)
                         VALUES(?,?,?,?,?,?)""",
                      (chat_id,pack_name or "",file_id,file_unique_id,emoji or "",time.time()))
