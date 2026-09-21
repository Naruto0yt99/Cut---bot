import asyncio, random, json, time
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ChatPermissions
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
    known_games=games.recent_games(message.chat.id)
    return await call_ai(SYSTEM_PROMPT+"\n"+format_style(),message.from_user,message.chat,
        f"Mode: {mode}\nMember profile: {profile}\nKnown games: {known_games}\nExtra: {extra}\nCurrent message: {message.text or ''}",
        recent,memories)

def conversation_signal(message):
    t=(message.text or "").lower()
    return any(x in t for x in ("game","khel","kaise start","rules","turn","guess","round","score","chal"))

def should_reply(message):
    text=(message.text or "").strip()
    if not text or text.startswith("/") or not message.from_user or message.from_user.is_bot: return False
    if message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id==bot.id: return True
    if settings.bot_username and f"@{settings.bot_username.lower()}" in text.lower(): return True
    if conversation_signal(message): return random.random()<0.72
    return random.random()<settings.reply_probability

async def learn_or_update_game(message):
    from provider import raw_ai
    recent=memory.recent(message.chat.id,40)
    transcript="\n".join(f"{n}: {t}" for n,t in recent)
    prompt=f"""Analyze this Telegram conversation as a game-learning assistant.
Conversation:
{transcript}
Return JSON only:
{{"is_game":true/false,"name":"...","rules":"only demonstrated rules","missing_questions":["..."],"confidence":0.0}}
Do not invent rules. If people are merely discussing a game, confidence should stay low.
"""
    try:
        data=json.loads(await raw_ai(prompt))
        if not data.get("is_game") or not data.get("name") or float(data.get("confidence",0))<0.60:
            return None
        gid=games.upsert(message.chat.id,data["name"],data.get("rules",""),"learned" if float(data["confidence"])>=0.85 else "learning",float(data["confidence"]),message.from_user.id)
        for name,text in recent[-15:]:
            games.add_turn(gid,message.from_user.id,name,text)
        questions=data.get("missing_questions") or []
        if questions and float(data["confidence"])<0.90:
            return "Mujhe game ka idea samajh aa raha hai... 👀\nBas ek cheez clear kar do: "+str(questions[0])
        return None
    except Exception as exc:
        print("Game learning error:",repr(exc))
        return None

@dp.message(Command("start"))
async def is_admin(message:Message):
    if not message.from_user or message.chat.type=="private":
        return False
    try:
        member=await bot.get_chat_member(message.chat.id,message.from_user.id)
        return member.status in ("creator","administrator")
    except Exception:
        return False

def target_user(message:Message):
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user
    return None

@dp.message(Command("birthday"))
async def birthday(message:Message):
    target=target_user(message) or message.from_user
    parts=(message.text or "").split(maxsplit=1)
    if len(parts)<2:
        profile=social.member(message.chat.id,target.id)
        date=profile[3] if profile else ""
        await message.answer(f"Birthday: {date or 'abhi yaad nahi hai...'}")
        return
    date=parts[1].strip()
    social.set_birthday(message.chat.id,target.id,date)
    await message.answer(f"Yaad rakh liya... 🎂 {target.full_name} ka birthday {date} hai...")

@dp.message(Command("mute"))
async def mute(message:Message):
    if not await is_admin(message):
        await message.answer("Ye command sirf actual group admins use kar sakte hain...")
        return
    target=target_user(message)
    if not target:
        await message.answer("Jisko mute karna hai uske message ko reply karke /mute [minutes] bhejo...")
        return
    parts=(message.text or "").split()
    minutes=10
    if len(parts)>1:
        try: minutes=max(1,min(int(parts[1]),1440))
        except ValueError: pass
    try:
        await bot.restrict_chat_member(message.chat.id,target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=time.time()+minutes*60)
        await message.answer(f"{target.full_name} ko {minutes} min ke liye mute kar diya...")
    except Exception as exc:
        await message.answer("Mute nahi ho paya... bot ko restrict-members permission chahiye.")
        print("Mute error:",repr(exc))

@dp.message(Command("unmute"))
async def unmute(message:Message):
    if not await is_admin(message):
        await message.answer("Ye command sirf actual group admins use kar sakte hain...")
        return
    target=target_user(message)
    if not target:
        await message.answer("Unmute ke liye target ke message ko reply karo...")
        return
    try:
        await bot.restrict_chat_member(message.chat.id,target.id,
            permissions=ChatPermissions(can_send_messages=True,can_send_audios=True,can_send_documents=True,
            can_send_photos=True,can_send_videos=True,can_send_video_notes=True,can_send_voice_notes=True,
            can_send_polls=True,can_send_other_messages=True,can_add_web_page_previews=True,can_change_info=False,
            can_invite_users=True,pin_messages=False))
        await message.answer(f"{target.full_name} ko unmute kar diya...")
    except Exception as exc:
        await message.answer("Unmute nahi ho paya... bot ki group permissions check karo.")
        print("Unmute error:",repr(exc))

@dp.message(Command("ban"))
async def ban(message:Message):
    if not await is_admin(message):
        await message.answer("Ye command sirf actual group admins use kar sakte hain...")
        return
    target=target_user(message)
    if not target:
        await message.answer("Ban ke liye target ke message ko reply karo...")
        return
    try:
        await bot.ban_chat_member(message.chat.id,target.id)
        await message.answer(f"{target.full_name} ko group se ban kar diya...")
    except Exception as exc:
        await message.answer("Ban nahi ho paya... bot ko ban-users permission chahiye.")
        print("Ban error:",repr(exc))

@dp.message(Command("unban"))
async def unban(message:Message):
    if not await is_admin(message):
        await message.answer("Ye command sirf actual group admins use kar sakte hain...")
        return
    target=target_user(message)
    if not target:
        await message.answer("Unban ke liye user ke message ko reply karo...")
        return
    try:
        await bot.unban_chat_member(message.chat.id,target.id,only_if_banned=True)
        await message.answer(f"{target.full_name} ko unban kar diya...")
    except Exception as exc:
        await message.answer("Unban nahi ho paya...")
        print("Unban error:",repr(exc))

@dp.message(Command("profile"))
async def profile(message:Message):
    target=target_user(message) or message.from_user
    row=social.member(message.chat.id,target.id)
    if not row:
        await message.answer("Abhi is member ki memory me kuch saved nahi hai...")
        return
    name,username,facts,bday=row
    await message.answer(f"👤 {name}\nUsername: @{username or 'none'}\n🎂 {bday or 'unknown'}\n🧠 {facts or 'abhi koi saved fact nahi...'}")

async def start(message:Message):
    await message.answer("Hii... main yahin hoon... 🌸\nMain AI bot hoon... group me friendly member ki tarah baat karne ke liye bani hoon...")

@dp.message(Command("game"))
async def game(message:Message):
    known=games.recent_games(message.chat.id)
    await message.answer(("Mujhe ye games yaad hain... 🎮\n"+", ".join(x[1] for x in known[:8])) if known else "Abhi koi game properly learn nahi hua... examples dikhao, main rules samajhungi... 👀")

@dp.message(Command("play"))
async def play_game(message:Message):
    known=games.recent_games(message.chat.id)
    if not known:
        await message.answer("Abhi koi game saved nahi hai... pehle mujhe game samajhne do 👀")
        return
    game=known[0]
    if game[3]!="learned" or game[4]<0.85:
        await message.answer("Is game ko abhi poora nahi samjhi hoon... ek-do cheez aur dikha do, phir properly khelenge 🎮")
        return
    session=games.start_session(game[0],message.chat.id)
    games.add_turn(game[0],message.from_user.id,message.from_user.full_name,"started game")
    await message.answer(f"Chalo {game[1]} khelte hain... 🎮")
    await run_active_game(message)

@dp.message(Command("stopgame"))
async def stop_game(message:Message):
    active=games.active_session(message.chat.id)
    if active:
        games.finish_session(active[0])
        await message.answer("Theek hai... game pause kar diya 😌")
    else:
        await message.answer("Abhi koi active game nahi hai...")

@dp.message(Command("games"))
async def games_cmd(message:Message):
    known=games.recent_games(message.chat.id)
    if not known: return await message.answer("Abhi koi game saved nahi hai...")
    await message.answer("Mujhe ye games yaad hain... 🎮\n"+"\n".join(f"• {x[1]} — {x[3]} ({x[4]:.0%})" for x in known))

@dp.message(F.sticker)
async def sticker_message(message:Message):
    s=message.sticker
    stickers.add(message.chat.id,s.set_name,s.file_id,s.file_unique_id,s.emoji)
    if s.set_name:
        try:
            for item in await get_pack_stickers(bot,s.set_name):
                stickers.add(message.chat.id,s.set_name,item.file_id,item.file_unique_id,item.emoji)
        except Exception as exc: print("Sticker pack error:",repr(exc))

@dp.message(F.text)
async def text_message(message:Message):
    if not message.from_user: return
    social.touch(message.chat.id,message.from_user.id,message.from_user.full_name,message.from_user.username or "")
    memory.add_message(message)

    if conversation_signal(message):
        learned_reply=await learn_or_update_game(message)
        if learned_reply and proactive.cooldown(proactive.last_question,message.chat.id,180):
            await message.reply(learned_reply)
            memory.add_bot_message(message.chat.id,learned_reply)
            return

    if await run_active_game(message): return
    if not should_reply(message): return
    try:
        reply=await ai_reply(message)
        if reply:
            await message.reply(reply.strip())
            memory.add_bot_message(message.chat.id,reply)
    except Exception as exc: print("AI error:",repr(exc))

async def proactive_loop():
    while True:
        try:
            now=time.time()
            for chat_id in memory.known_chats():
                if chat_id > 0: continue
                if now-memory.last_activity(chat_id) < 1800: continue
                if not proactive.cooldown(proactive.last_spontaneous,chat_id,21600): continue
                recent=memory.recent(chat_id,12)
                fake=type("U",(),{"full_name":"group"})()
                reply=await ai_reply(type("M",(),{"chat":type("C",(),{"id":chat_id})(),"from_user":fake,"text":""})(),"proactive","The group has been quiet for 30+ minutes. Start a short, relevant, clean conversation or offer a known game. Do not mention being scheduled.")
                if reply:
                    await bot.send_message(chat_id,reply)
                    memory.add_bot_message(chat_id,reply)
        except Exception as exc: print("Proactive loop error:",repr(exc))
        await asyncio.sleep(90)

async def main():
    me=await bot.get_me()
    settings.bot_username=me.username or ""
    print(f"Bot online: @{settings.bot_username}")
    asyncio.create_task(proactive_loop())
    await dp.start_polling(bot,allowed_updates=dp.resolve_used_update_types())

if __name__=="__main__":
    asyncio.run(main())
