import time

class ProactiveState:
    def __init__(self):
        self.last_reply={}
        self.last_question={}
        self.last_spontaneous={}
        self.active_game={}

    def cooldown(self, table, chat_id, seconds):
        now=time.time()
        if now-table.get(chat_id,0)<seconds:
            return False
        table[chat_id]=now
        return True
