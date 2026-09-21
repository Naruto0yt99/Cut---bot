import asyncio, random, json, time
from datetime import timedelta
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
from scheduler import birthday_loop

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
    return await call_ai(
        SYSTEM_PROMPT+"\n"+format_style(),
        message.from_user,
        message.chat,
        f"Mode: {mode}\nMember profile: {profile}\nKnown games: {known_games}\nExtra: {extra}\nCurrent message: {message.text or ''}",
        recent,
        memories,
    )

def conversation_signal(message):
    t=(message.text or "").lower()
    return any(x in t for x in (
        "game","khel","kaise start","rules","turn","guess","round","score",
        "chal","playing","khel rahe","match","quiz","puzzle","challenge"
    ))

def looks_like_game_activity(message):
    t=(message.text or "").lower()
    quoted=(message.reply_to_message.text or "").lower() if message.reply_to_message else ""
    return conversation_signal(message) or any(
        x in quoted for x in ("game","khel","turn","guess","round","score","quiz","puzzle")
    )

def should_reply(message):
    text=(message.text or "").strip()
    if not text or text.startswith("/") or not message.from_user or message.from_user.is_bot:
        return False
    if message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id==bot.id:
        return True
    if settings.bot_username and f"@{settings.bot_username.lower()}" in text.lower():
        return True
    if conversation_signal(message):
        return random.random()<0.72
    return random.random()<settings.reply_probability

async def run_active_game(message:Message):
    from provider import raw_ai
    from game_engine import plan_turn
    active=games.active_session(message.chat.id)
    if not active:
        return False
    session_id,game_id,_,current_player,state=active
    rows=games.recent_games(message.chat.id)
    game=next((x for x in rows if x[0]==game_id),None)
    if not game:
        games.finish_session(session_id)
        return False
    games.add_turn(game_id,message.from_user.id,message.from_user.full_name,message.text or "")
    turns=games.turns(game_id,30)
    transcript="\n".join(f"{speaker}: {text}" for _,speaker,text in turns)
    plan=await plan_turn(raw_ai,game[1],game[2],transcript)
    confidence=float(plan.get("confidence",0) or 0)
    action=plan.get("action","ask")
    if action=="ask" or confidence<0.75:
        q=str(plan.get("message") or "Ek rule clear kar do, phir main properly khelungi ???")
        if proactive.cooldown(proactive.last_question,message.chat.id,180):
            await message.reply(q)
            memory.add_bot_message(message.chat.id,q)
        return True
    if action=="play":
        out=str(plan.get("message") or "").strip()
        if out:
            await message.reply(out)
            memory.add_bot_message(message.chat.id,out)
            games.add_turn(game_id,0,"AI",out)
        games.update_session(session_id,plan.get("next_player"),str(plan.get("state") or state or ""))
    elif action=="wait":
        games.update_session(session_id,plan.get("next_player"),str(plan.get("state") or state or ""))
    if str(plan.get("status","")).lower() in ("finished","done","ended"):
        games.finish_session(session_id)
    return True

async def maybe_join_game(message:Message):
    if games.active_session(message.chat.id):
        return False
    recent=memory.recent(message.chat.id,12)
    if len(recent)<3 or not looks_like_game_activity(message):
        return False
    from provider import raw_ai
    transcript="\n".join(f"{n}: {t}" for n,t in recent)
    prompt=f"""Decide whether people are actively playing a known Telegram game.
Known games: {games.recent_games(message.chat.id)}
Recent chat:
{transcript}
Return JSON only: {{"playing":true/false,"game_name":"name or empty","confidence":0.0}}
Do not infer a game merely from the word 'game'."""
    try:
        data=json.loads(await raw_ai(prompt))
        if not data.get("playing") or float(data.get("confidence",0))<0.88:
            return False
        name=data.get("game_name","")
        row=games.find(message.chat.id,name) if name else None
        if not row or row[3]!="learned" or row[4]<0.85:
            return False
        games.start_session(row[0],message.chat.id)
        games.add_turn(row[0],message.from_user.id,message.from_user.full_name,"bot joined observed game")
        await message.reply(f"Achaaa... ye {row[1]} wala game chal raha hai 😭🎮 Main bhi join kar rahi hoon...")
        await run_active_game(message)
        return True
    except Exception as exc:
        print("Game join detection error:",repr(exc))
        return False

async def learn_or_update_game(message:Message):
    from provider import raw_ai
    recent=memory.recent(message.chat.id,40)
    transcript="\n".join(f"{n}: {t}" for n,t in recent)
    prompt=f"""Analyze this Telegram conversation as a game-learning assistant.
Conversation:
{transcript}
Return JSON only:
{{"is_game":true/false,"name":"...","rules":"only demonstrated rules","missing_questions":["..."],"confidence":0.0}}
Do not invent rules. If people are merely discussing a game, confidence should stay low."""
    try:
        data=json.loads(await raw_ai(prompt))
        confidence=float(data.get("confidence",0) or 0)
        if not data.get("is_game") or not data.get("name") or confidence<0.60:
            return None
        gid=games.upsert(
            message.chat.id,data["name"],data.get("rules",""),
            "learned" if confidence>=0.85 else "learning",
            confidence,message.from_user.id
        )
        for name,text in recent[-15:]:
            games.add_turn(gid,message.from_user.id,name,text)
        questions=data.get("missing_questions") or []
        if questions and confidence<0.90:
            return "Mujhe game ka idea samajh aa raha hai... 👀\nBas ek cheez clear kar do: "+str(questions[0])
        return None
    except Exception as exc:
        print("Game learning error:",repr(exc))
        return None

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

@dp.message(Command("start"))
async def start(message:Message):
    await message.answer(
        "Hii... main yahin hoon... 🌸\n"
        "Main AI bot hoon... group me friendly member ki tarah baat karne ke liye bani hoon..."
    )

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

@dp.message(Command("profile"))
async def profile(message:Message):
    target=target_user(message) or message.from_user
    row=social.member(message.chat.id,target.id)
    if not row:
        await message.answer("Abhi is member ki memory me kuch saved nahi hai...")
        return
    name,username,facts,bday=row
    await message.answer(
        f"👤 {name}\nUsername: @{username or 'none'}\n"
        f"🎂 {bday or 'unknown'}\n🧠 {facts or 'abhi koi saved fact nahi...'}"
    )

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
        try:
            minutes=max(1,min(int(parts[1]),1440))
        except ValueError:
            pass
    try:
        await bot.restrict_chat_member(
            message.chat.id,target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=timedelta(minutes=minutes)
        )
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
        await bot.restrict_chat_member(
            message.chat.id,target.id,
           permissions=ChatPermissions(
                can_send_messages=True,can_send_audios=True,can_send_documents=True,
                can_send_photos=True,can_send_videos=True,can_send_video_notes=True,
                can_send_voice_notes=True,can_send_polls=True,can_send_other_messages=True,
                can_add_web_page_previews=True,can_invite_users=True
            )
        )
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

@dp.message(Command("game"))
async def game(message:Message):
    known=games.recent_games(message.chat.id)
    await message.answer(
        ("Mujhe ye games yaad hain... 🎮\n"+", ".join(x[1] for x in known[:8]))
        if known else
        "Abhi koi game properly learn nahi hua... examples dikhao, main rules samajhungi... 👀"
    )

@dp.message(Command("games"))
async def games_cmd(message:Message):
    known=games.recent_games(message.chat.id)
    if not known:
        await message.answer("Abhi koi game saved nahi hai...")
        return
    await message.answer(
        "Mujhe ye games yaad hain... 🎮\n"+
        "\n".join(f"• {x[1]} — {x[3]} ({x[4]:.0%})" for x in known)
    )

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
    games.start_session(game[0],message.chat.id)
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

@dp.message(F.sticker)
async def sticker_message(message:Message):
    s=message.sticker
    stickers.add(message.chat.id,s.set_name,s.file_id,s.file_unique_id,s.emoji,safe=1)
    if s.set_name:
        try:
            for item in await get_pack_stickers(bot,s.set_name):
                stickers.add(message.chat.id,s.set_name,item.file_id,item.file_unique_id,item.emoji,safe=1)
        except Exception as exc:
            print("Sticker pack error:",repr(exc))

@dp.message(Command("sticker"))
async def sticker_cmd(message:Message):
    parts=(message.text or "").split(maxsplit=1)
    emoji=parts[1].strip()[:8] if len(parts)>1 else None
    items=stickers.candidates(message.chat.id,emoji,12)
    if not items:
        await message.answer("Abhi suitable sticker nahi mila... pehle group me sticker packs use hone do 😄")
        return
    item=random.choice(items)
    await bot.send_sticker(message.chat.id,item[0])
    stickers.mark_used(item[1])

@dp.message(F.text)
async def text_message(message:Message):
    if not message.from_user or message.from_user.is_bot:
        return
    social.touch(message.chat.id,message.from_user.id,message.from_user.full_name,message.from_user.username or "")
    memory.add_message(message)

    if conversation_signal(message):
        learned_reply=await learn_or_update_game(message)
        if learned_reply and proactive.cooldown(proactive.last_question,message.chat.id,180):
            await message.reply(learned_reply)
            memory.add_bot_message(message.chat.id,learned_reply)
            return

    if await run_active_game(message):
        return
    if await maybe_join_game(message):
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

async def proactive_loop():
    while True:
        try:
            now=time.time()
            for chat_id in memory.known_chats():
                if chat_id > 0:
                    continue
                if now-memory.last_activity(chat_id)<1800:
                    continue
                if not proactive.cooldown(proactive.last_spontaneous,chat_id,21600):
                    continue
                fake=type("U",(),{"full_name":"group"})()
                fake_message=type("M",(),{
                    "chat":type("C",(),{"id":chat_id})(),
                    "from_user":fake,
                    "text":""
                })()
                reply=await ai_reply(
                    fake_message,
                    "proactive",
                    "The group has been quiet for 30+ minutes. Start a short, relevant, clean conversation or offer a known game. Do not mention being scheduled."
                )
                if reply:
                    await bot.send_message(chat_id,reply)
                    memory.add_bot_message(chat_id,reply)
        except Exception as exc:
            print("Proactive loop error:",repr(exc))
        await asyncio.sleep(90)

async def health_server():
    """Small HTTP server so Render Web Service has a listening port."""
    port = int(__import__("os").environ.get("PORT", "8080"))

    async def handle(reader, writer):
        try:
            request = await asyncio.wait_for(reader.read(1024), timeout=2)
            first_line = request.decode("utf-8", "ignore").splitlines()[0] if request else ""
            path = first_line.split(" ")[1] if len(first_line.split(" ")) >= 2 else "/"
            if path == "/healthz":
                body = b"ok"
                status = b"200 OK"
            else:
                body = b"Mimi is online"
                status = b"200 OK"
            response = (
                b"HTTP/1.1 " + status + b"\\r\\n"
                b"Content-Type: text/plain; charset=utf-8\\r\\n"
                b"Content-Length: " + str(len(body)).encode() + b"\\r\\n"
                b"Connection: close\\r\\n\\r\\n" + body
            )
            writer.write(response)
            await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    server = await asyncio.start_server(handle, "0.0.0.0", port)
    print(f"Health server listening on 0.0.0.0:{port}")
    async with server:
        await server.serve_forever()

async def main():
    me=await bot.get_me()
    settings.bot_username=me.username or ""
    print(f"Bot online: @{settings.bot_username}")
    asyncio.create_task(health_server())
    asyncio.create_task(proactive_loop())
    asyncio.create_task(birthday_loop(bot,social,memory))
    await dp.start_polling(bot,allowed_updates=dp.resolve_used_update_types())

if __name__=="__main__":
    asyncio.run(main())
