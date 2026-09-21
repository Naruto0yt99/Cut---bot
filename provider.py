from google import genai
from google.genai import types
from personality import SYSTEM_PROMPT
from config import settings

client=genai.Client(api_key=settings.gemini_api_key)

def generate_reply(current_name:str,current_text:str,recent,relevant):
    recent_text="\n".join(f"{n}: {m}" for n,m in recent[-30:])
    relevant_text="\n".join(f"{n}: {m}" for n,m in relevant)
    prompt=f"""Current speaker: {current_name}
Current message: {current_text}

Recent group conversation:
{recent_text}

Potentially relevant older memory:
{relevant_text}

Decide whether replying adds value. If not, return exactly NO_REPLY.
"""
    r=client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT,temperature=0.75,max_output_tokens=350)
    )
    out=(r.text or "").strip()
    return "NO_REPLY" if out.upper()=="NO_REPLY" else out
