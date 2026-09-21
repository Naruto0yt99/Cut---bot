import sqlite3, time
from pathlib import Path

class GameMemory:
    def __init__(self, db_url):
        self.path=Path(db_url.replace("sqlite:///",""))
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS games(
                id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL,
                name TEXT NOT NULL, rules TEXT DEFAULT '', status TEXT DEFAULT 'learning',
                confidence REAL DEFAULT 0, created_by INTEGER, updated_at REAL)""")
            c.execute("""CREATE TABLE IF NOT EXISTS game_turns(
                id INTEGER PRIMARY KEY AUTOINCREMENT, game_id INTEGER NOT NULL,
                user_id INTEGER, speaker TEXT, text TEXT, created_at REAL)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_game_chat ON games(chat_id,updated_at)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_game_turns ON game_turns(game_id,created_at)")
            c.execute("""CREATE TABLE IF NOT EXISTS game_sessions(
                id INTEGER PRIMARY KEY AUTOINCREMENT, game_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL, status TEXT DEFAULT 'active',
                current_player INTEGER, state TEXT DEFAULT '', started_at REAL, updated_at REAL)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_game_sessions ON game_sessions(chat_id,status)")

    def find(self, chat_id, name):
        with sqlite3.connect(self.path) as c:
            return c.execute("SELECT id,name,rules,status,confidence,created_by,updated_at FROM games WHERE chat_id=? AND lower(name)=lower(?) ORDER BY updated_at DESC LIMIT 1",(chat_id,name)).fetchone()

    def recent_games(self, chat_id, limit=10):
        with sqlite3.connect(self.path) as c:
            return c.execute("SELECT id,name,rules,status,confidence FROM games WHERE chat_id=? ORDER BY updated_at DESC LIMIT ?",(chat_id,limit)).fetchall()

    def upsert(self, chat_id, name, rules, status, confidence, user_id):
        now=time.time()
        old=self.find(chat_id,name)
        with sqlite3.connect(self.path) as c:
            if old:
                c.execute("UPDATE games SET rules=?,status=?,confidence=?,updated_at=? WHERE id=?",(rules,status,confidence,now,old[0]))
                return old[0]
            cur=c.execute("INSERT INTO games(chat_id,name,rules,status,confidence,created_by,updated_at) VALUES(?,?,?,?,?,?,?)",(chat_id,name,rules,status,confidence,user_id,now))
            return cur.lastrowid

    def add_turn(self, game_id, user_id, speaker, text):
        with sqlite3.connect(self.path) as c:
            c.execute("INSERT INTO game_turns(game_id,user_id,speaker,text,created_at) VALUES(?,?,?,?,?)",(game_id,user_id,speaker,text,time.time()))

    def turns(self, game_id, limit=30):
        with sqlite3.connect(self.path) as c:
            rows=c.execute("SELECT user_id,speaker,text FROM game_turns WHERE game_id=? ORDER BY id DESC LIMIT ?",(game_id,limit)).fetchall()
        return list(reversed(rows))

    def start_session(self,game_id,chat_id):
        now=time.time()
        with sqlite3.connect(self.path) as c:
            c.execute("UPDATE game_sessions SET status='finished',updated_at=? WHERE chat_id=? AND status='active'",(now,chat_id))
            cur=c.execute("INSERT INTO game_sessions(game_id,chat_id,status,started_at,updated_at) VALUES(?,?,?,?,?)",(game_id,chat_id,"active",now,now))
            return cur.lastrowid

    def active_session(self,chat_id):
        with sqlite3.connect(self.path) as c:
            return c.execute("SELECT id,game_id,status,current_player,state FROM game_sessions WHERE chat_id=? AND status='active' ORDER BY id DESC LIMIT 1",(chat_id,)).fetchone()

    def update_session(self,session_id,current_player,state):
        with sqlite3.connect(self.path) as c:
            c.execute("UPDATE game_sessions SET current_player=?,state=?,updated_at=? WHERE id=?",(current_player,state,time.time(),session_id))

    def finish_session(self,session_id):
        with sqlite3.connect(self.path) as c:
            c.execute("UPDATE game_sessions SET status='finished',updated_at=? WHERE id=?",(time.time(),session_id))
