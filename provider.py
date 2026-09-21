import asyncio
from google import genai
from google.genai import types
from config import settings

client=genai.Client(api_key=settings.gemini_api_key)

# Gemini can occasionally return transient 503/UNAVAILABLE errors under load.
# Keep the configured model as the primary model, then use a stable fallback.
FALLBACK_MODEL="gemini-2.5-flash-lite"

def _is_transient(exc):
    text=str(exc).upper()
    return any(x in text for x in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "500", "504", "DEADLINE_EXCEEDED"))

async def _generate(model,prompt,system_instruction=""):
    return await client.aio.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.35,
            max_output_tokens=500,
        )
    )

async def raw_ai(prompt, system_instruction=""):
    models=[settings.gemini_model]
    if FALLBACK_MODEL not in models:
        models.append(FALLBACK_MODEL)

    last_exc=None
    for model in models:
        for attempt in range(3):
            try:
                response=await _generate(model,prompt,system_instruction)
                return (response.text or "").strip()
            except Exception as exc:
                last_exc=exc
                if not _is_transient(exc):
                    raise
                delay=1.5*(2**attempt)
                print(f"Gemini transient error on {model} (attempt {attempt+1}/3): {exc}")
                await asyncio.sleep(delay)

    raise last_exc

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
    out=await raw_ai(prompt,system_prompt)
    if out.upper()=="NO_REPLY" or not out:
        return None
    return out
