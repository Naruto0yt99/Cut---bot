import json

async def plan_turn(raw_ai, game_name, rules, transcript):
    prompt=f"""You are a Telegram game engine.
Game: {game_name}
Learned rules:
{rules}
Recent turns:
{transcript}

Choose only a legal next action supported by the rules. If rules are incomplete, ask one precise clarification question.
Return JSON only: {{"action":"play|ask|wait","message":"short message","state":"brief state update","confidence":0.0}}
Never invent missing rules."""
    raw=await raw_ai(prompt)
    try:
        data=json.loads(raw)
        if isinstance(data,dict): return data
    except Exception: pass
    return {"action":"ask","message":"Ek rule clear kar do, phir main properly khelungi ???","state":"","confidence":0.0}
