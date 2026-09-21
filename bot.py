import asyncio, random
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from config import settings
from memory import MemoryStore
from social_memory import SocialMemory
from personality import SYSTEM_PROMPT, format_style
from sticker_store import StickerStore
from sticker_pack import get_pack_stickers
from games import new_word_game, new_character_game

bot=Bot(settings.bot_token)
dp=Dispatcher()
memory=MemoryStore(settings.database_url)
social=SocialMemory(settings.database_url)
stickers=StickerStore(settings.database_url)

async def ai_reply(message:Message):
    from provider import call_ai
    recent=memory.recent(message.chat.id,20)
    memories=memory.relevant(message.chat.id,message.from_user.id,message.text or "")
    profile=social.member(message.chat.id,message.from_user.id)
    profile_text=str(profile) if profile else "new member"
    return await call_ai(SYSTEM_PROMPT+"\n"+format_style(),
                         message.from_user,message.chat,
                         f"Member profile: {profile_text}\nMessage: {message.text or ''}",
                         recent,memories)

def should_reply(message:Message):
    text=(message.text or "").strip()
    if not text or text.startswith("/") or not message.from_user or message.from_user.is_bot:
        return False
    if message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id==bot.id:
        return True
    username=settings.bot_username
    if username and f"@{username.lower()}" in text.lower():
        return True
    return random.random()<settings.reply_probability

@dp.message(Command("start"))
async def start(message:Message):
    await message.answer("Hii... main yahin hoon... 🌸\nMain AI bot hoon, group me friendly member ki tarah baat karne ke liye bani hoon...")

@dp.message(Command("game"))
async def game(message:Message):
    await message.answer(f"Chalo game... 😼\nWord hint: {new_word_game()} ???")

@dp.message(Command("char"))
async def char_game(message:Message):
    await message.answer(f"Anime character guess karo... 👀\nCharacter: {new_character_game()}")

@dp.message(F.sticker)
async def sticker_message(message:Message):
    s=message.sticker
    stickers.add(message.chat.id,s.set_name,s.file_id,s.file_unique_id,s.emoji)
    if s.set_name:
        try:
            pack=await get_pack_stickers(bot,s.set_name)
            for item in pack:
                stickers.add(message.chat.id,s.set_name,item.file_id,item.file_unique_id,item.emoji)
        except Exception as exc:
            print("Sticker pack error:",repr(exc))

@dp.message(F.text)
async def text_message(message:Message):
    if not message.from_user:
        return
    social.touch(message.chat.id,message.from_user.id,message.from_user.full_name,
                 message.from_user.username or "")
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
