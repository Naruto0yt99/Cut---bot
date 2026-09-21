import json

async def learn_game(call_ai, game_name, recent_messages, existing_rules=""):
    transcript="\n".join(f"{speaker}: {text}" for speaker,text in recent_messages[-40:])
    prompt=f"""You are learning a Telegram group game from real examples.
Game name: {game_name}
Existing rules:
{existing_rules or "(none)"}

Recent observed conversation:
{transcript}

Infer only what is actually supported by the examples. Identify:
1) objective
2) setup/start procedure
3) turn order
4) legal actions
5) how answers/winners are determined
6) what information the bot still needs to ask a human about
7) one or two example turns

Return JSON only with keys:
name, rules, questions, confidence
Do not invent missing rules. confidence must be 0..1.
"""
    raw=await call_ai(prompt)
    try:
        data=json.loads(raw)
        if isinstance(data,dict):
            return data
    except Exception:
        pass
    return {"name":game_name,"rules":existing_rules,"questions":["Game ka exact start kaise hota hai ???","Ek turn me player kya karta hai ???"],"confidence":0.0}
