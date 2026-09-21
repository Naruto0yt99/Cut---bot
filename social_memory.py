import sqlite3, time
from pathlib import Path

class SocialMemory:
    def __init__(self, db_url):
        self.path=Path(db_url.replace("sqlite:///",""))
        with sqlite3.connect(self.path) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS members(
                chat_id INTEGER,user_id INTEGER,name TEXT,username TEXT,
                facts TEXT DEFAULT '',birthday TEXT DEFAULT '',last_seen REAL,
                PRIMARY KEY(chat_id,user_id))""")
            c.execute("""CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,chat_id INTEGER,user_id INTEGER,
                kind TEXT,event_date TEXT,note TEXT,created_at REAL)""")

    def touch(self, chat_id,user_id,name,username):
        with sqlite3.connect(self.path) as c:
            c.execute("""INSERT INTO members(chat_id,user_id,name,username,last_seen)
                VALUES(?,?,?,?,?) ON CONFLICT(chat_id,user_id) DO UPDATE SET
                name=excluded.name,username=excluded.username,last_seen=excluded.last_seen""",
                (chat_id,user_id,name,username,time.time()))

    def member(self,chat_id,user_id):
        with sqlite3.connect(self.path) as c:
            return c.execute("SELECT name,username,facts,birthday FROM members WHERE chat_id=? AND user_id=?",
                             (chat_id,user_id)).fetchone()

    def set_birthday(self,chat_id,user_id,date):
        with sqlite3.connect(self.path) as c:
            c.execute("UPDATE members SET birthday=? WHERE chat_id=? AND user_id=?",
                      (date,chat_id,user_id))

    def add_event(self,chat_id,user_id,kind,date,note=""):
        with sqlite3.connect(self.path) as c:
            c.execute("""INSERT INTO events(chat_id,user_id,kind,event_date,note,created_at)
                         VALUES(?,?,?,?,?,?)""",(chat_id,user_id,kind,date,note,time.time()))
