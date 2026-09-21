import sqlite3, time, re
from pathlib import Path

class MemoryStore:
    def __init__(self, db_url:str):
        self.path=Path(db_url.replace("sqlite:///",""))
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL,
                user_id INTEGER, name TEXT, username TEXT, text TEXT,
                created_at REAL NOT NULL)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_chat_time ON messages(chat_id,created_at)")

    def add_message(self,message):
        u=message.from_user
        text=message.text or message.caption or ""
        with sqlite3.connect(self.path) as c:
            c.execute("""INSERT INTO messages(chat_id,user_id,name,username,text,created_at)
                         VALUES(?,?,?,?,?,?)""",(message.chat.id,u.id,u.full_name,u.username or "",text,time.time()))

    def add_bot_message(self,chat_id:int,text:str):
        with sqlite3.connect(self.path) as c:
            c.execute("""INSERT INTO messages(chat_id,user_id,name,username,text,created_at)
                         VALUES(?,?,?,?,?,?)""",(chat_id,0,"AI","",text,time.time()))

    def recent(self,chat_id:int,limit:int=20):
        with sqlite3.connect(self.path) as c:
            rows=c.execute("SELECT name,text FROM messages WHERE chat_id=? ORDER BY id DESC LIMIT ?",(chat_id,limit)).fetchall()
        return list(reversed(rows))

    def relevant(self,chat_id:int,user_id:int,text:str,limit:int=12):
        words={w.lower() for w in re.findall(r"[A-Za-z0-9_]{3,}",text)}
        with sqlite3.connect(self.path) as c:
            rows=c.execute("SELECT name,text FROM messages WHERE chat_id=? ORDER BY id DESC LIMIT 500",(chat_id,)).fetchall()
        scored=[]
        for name,msg in rows:
            score=sum(w in (msg or "").lower() for w in words)
            if score: scored.append((score,name,msg))
        scored.sort(key=lambda x:x[0],reverse=True)
        return [(n,m) for _,n,m in scored[:limit]]

    def known_chats(self):
        with sqlite3.connect(self.path) as c:
            return [r[0] for r in c.execute("SELECT DISTINCT chat_id FROM messages").fetchall()]

    def last_activity(self,chat_id):
        with sqlite3.connect(self.path) as c:
            row=c.execute("SELECT MAX(created_at) FROM messages WHERE chat_id=?",(chat_id,)).fetchone()
        return row[0] or 0
