import asyncio, datetime, sqlite3
from zoneinfo import ZoneInfo

IST=ZoneInfo("Asia/Kolkata")

async def birthday_loop(bot,social,memory):
    last_day=None
    while True:
        try:
            today=datetime.datetime.now(IST).strftime("%d-%m")
            if today!=last_day:
                last_day=today
                with sqlite3.connect(social.path) as c:
                    rows=c.execute("SELECT user_id,name FROM people WHERE birthday LIKE ?",(f"%{today}",)).fetchall()
                for chat_id in memory.known_chats():
                    if chat_id>0:
                        continue
                    for user_id,name in rows:
                        text=f"Arre aaj {name} ka birthday haiii... 🎂🥳 Sab wish karooo..."
                        await bot.send_message(chat_id,text)
                        memory.add_bot_message(chat_id,text)
        except Exception as exc:
            print("Birthday loop error:",repr(exc))
        await asyncio.sleep(60)
