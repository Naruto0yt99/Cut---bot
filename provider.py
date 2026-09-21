from google import genai
from google.genai import types
from config import settings

client=genai.Client(api_key=settings.gemini_api_key)

async def call_ai(system_prompt,user,chat,current_text,recent,memories):
    recent_text="\n".join(f"{name}: {text}" for name,text in recent)
    memory_text="\n".join(f"{name}: {text}" for name,text in memories)
    prompt=f"""Current speaker: {user.full_name}
Current message: {current_text}

Recent group conversation:
{recent_text}

Relevant memory for this member:
{memory_text}

Reply only if it is natural and useful in the current conversation. If not, return exactly NO_REPLY.
"""
    response=await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=system_prompt,temperature=0.75,max_output_tokens=350)
    )
    out=(response.text or "").strip()
    if out.upper()=="NO_REPLY" or not out:
        return None
    return out
