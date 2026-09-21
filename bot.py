import asyncio, random
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from config import settings
from memory import MemoryStore
from personality import SYSTEM_PROMPT, format_style
from sticker_store import StickerStore

bot=Bot(settings.bot_token)
dp=Dispatcher()
memory=MemoryStore(settings.database_url)
stickers=StickerStore(settings.database_url)

async def ai_reply(message:Message):
    from provider import call_ai
    recent=memory.recent(message.chat.id,20)
    memories=memory.relevant(message.chat.id,message.from_user.id,message.text or "")
    return await call_ai(SYSTEM_PROMPT+"\n"+format_style(),message.from_user,
                         message.chat,message.text or "",recent,memories)

def should_reply(message:Message):
    text=(message.text or "").strip()
    if not text or text.startswith("/") or not message.from_user or message.from_user.is_bot:
        return False
    if message.reply_to_message and message.reply_to_message.from_user:
        if message.reply_to_message.from_user.id==bot.id:
            return True
    username=settings.bot_username
    if username and f"@{username.lower()}" in text.lower():
        return True
    return random.random()<settings.reply_probability

@dp.message(Command("start"))
async def start(message:Message):
    await message.answer("Hii... main yahin hoon... 🌸\nMain AI bot hoon, group me friendly member ki tarah baat karne ke liye bani hoon...")

@dp.message(F.sticker)
async def sticker_message(message:Message):
    s=message.sticker
    stickers.add(message.chat.id,s.set_name,s.file_id,s.file_unique_id,s.emoji)
    # Telegram file_id is kept; the sticker itself does not need to be downloaded to the phone.
    # Whole-pack indexing is done when the set is available through the Bot API.

@dp.message(F.text)
async def text_message(message:Message):
    if not message.from_user:
        return
    memory.add_message(message)
    if not should_reply(message):
        return
    try:
        reply=await ai_reply(message)
        if reply:
            await message.reply(reply.strip())
            memory.add_bot_message(message.chat.id,reply)
    except Exception as exc:
        print("AI error:",repr(exc))

async def main():
    me=await bot.get_me()
    settings.bot_username=me.username or ""
    print(f"Bot online: @{settings.bot_username}")
    await dp.start_polling(bot,allowed_updates=dp.resolve_used_update_types())

if __name__=="__main__":
    asyncio.run(main())
