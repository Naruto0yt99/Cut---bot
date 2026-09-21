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
from game_memory import GameMemory
from proactive import ProactiveState

bot=Bot(settings.bot_token)
dp=Dispatcher()
memory=MemoryStore(settings.database_url)
social=SocialMemory(settings.database_url)
stickers=StickerStore(settings.database_url)
games=GameMemory(settings.database_url)
proactive=ProactiveState()

async def ai_reply(message:Message, mode="normal", extra=""):
    from provider import call_ai
    recent=memory.recent(message.chat.id,30)
    memories=memory.relevant(message.chat.id,message.from_user.id,message.text or "",18)
    profile=social.member(message.chat.id,message.from_user.id)
    profile_text=str(profile) if profile else "new member"
    known_games=games.recent_games(message.chat.id)
    game_text="\n".join(str(x) for x in known_games) or "none"
    return await call_ai(
        SYSTEM_PROMPT+"\n"+format_style(),
        message.from_user,message.chat,
        f"""Mode: {mode}
Member profile: {profile_text}
Known games in this group: {game_text}
Extra instruction: {extra}
Current message: {message.text or ''}""",
        recent,memories)

def addressed(message):
    text=(message.text or "").lower()
    return bool(settings.bot_username and f"@{settings.bot_username.lower()}" in text)

def conversation_signal(message):
    text=(message.text or "").lower()
    return any(x in text for x in ("game","khel","kaise start","rules","turn","guess","round","score","chal"))

def should_reply(message):
    text=(message.text or "").strip()
    if not text or text.startswith("/") or not message.from_user or message.from_user.is_bot:
        return False
    if message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id==bot.id:
        return True
    if addressed(message):
        return True
    if conversation_signal(message):
        return random.random()<0.72
    return random.random()<settings.reply_probability

@dp.message(Command("start"))
async def start(message:Message):
    await message.answer("Hii... main yahin hoon... 🌸\nMain AI bot hoon... group me friendly member ki tarah baat karne ke liye bani hoon...")

@dp.message(Command("game"))
async def game(message:Message):
    known=games.recent_games(message.chat.id)
    if known:
        names=", ".join(x[1] for x in known[:5])
        await message.answer(f"Hamare known games: {names}... 😼")
    else:
        await message.answer("Koi game abhi properly learn nahi hua... mujhe examples dikhao, main rules samajhne ki koshish karungi... 👀")

@dp.message(Command("games"))
async def games_cmd(message:Message):
    known=games.recent_games(message.chat.id)
    if not known:
        await message.answer("Abhi koi game saved nahi hai...")
        return
    lines=["Mujhe ye games yaad hain... 🎮"]
    for _,name,rules,status,confidence in known:
        lines.append(f"• {name} — {status} ({confidence:.0%})")
    await message.answer("\n".join(lines))

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
    social.touch(message.chat.id,message.from_user.id,message.from_user.full_name,message.from_user.username or "")
    memory.add_message(message)

    text=(message.text or "").strip()
    if conversation_signal(message):
        known=games.recent_games(message.chat.id)
        if known:
            games.add_turn(known[0][0],message.from_user.id,message.from_user.full_name,text)
        elif any(x in text.lower() for x in ("game","khel","guess","round")):
            reply=await ai_reply(message,"game-learning","Figure out whether the group is teaching or playing a game. If unclear, ask its name. If enough evidence exists, ask one missing rule question. Do not pretend to know rules that have not been demonstrated.")
            if reply:
                await message.reply(reply)
                memory.add_bot_message(message.chat.id,reply)
                return

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
