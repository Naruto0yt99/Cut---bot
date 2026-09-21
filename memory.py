import sqlite3, time, re
from pathlib import Path

class Memory:
    def __init__(self, db_url:str):
        self.path=Path(db_url.replace("sqlite:///",""))
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, user_id INTEGER,
                name TEXT, username TEXT, text TEXT, created_at REAL)""")
            c.execute("""CREATE INDEX IF NOT EXISTS idx_messages_chat_time
                ON messages(chat_id,created_at)""")

    def add(self, chat_id:int,user_id:int,name:str,username:str,text:str):
        with sqlite3.connect(self.path) as c:
            c.execute("INSERT INTO messages(chat_id,user_id,name,username,text,created_at) VALUES(?,?,?,?,?,?)",
                      (chat_id,user_id,name,username,text,time.time()))

    def recent(self, chat_id:int, limit:int=30):
        with sqlite3.connect(self.path) as c:
            rows=c.execute("""SELECT name,text FROM messages WHERE chat_id=?
                              ORDER BY id DESC LIMIT ?""",(chat_id,limit)).fetchall()
        return list(reversed(rows))

    def relevant(self, chat_id:int, text:str, limit:int=12):
        words={w.lower() for w in re.findall(r"[A-Za-z0-9_]{3,}",text)}
        rows=self.recent(chat_id,150)
        scored=[]
        for name,msg in rows:
            score=sum(1 for w in words if w in msg.lower())
            if score: scored.append((score,name,msg))
        scored.sort(reverse=True)
        return [(n,m) for _,n,m in scored[:limit]]
