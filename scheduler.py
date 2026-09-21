import asyncio, random, time

class SocialScheduler:
    def __init__(self):
        self.last_action={}

    def allowed(self,chat_id,cooldown=3600):
        now=time.time()
        if now-self.last_action.get(chat_id,0)<cooldown:
            return False
        self.last_action[chat_id]=now
        return True

    async def idle_tick(self):
        await asyncio.sleep(30)
