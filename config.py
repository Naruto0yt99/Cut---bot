import os
from dataclasses import dataclass

@dataclass
class Settings:
    bot_token: str
    gemini_api_key: str
    gemini_model: str
    database_url: str = "bot_memory.db"
    reply_probability: float = 0.22
    bot_username: str = ""

    def __post_init__(self):
        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN missing. Add it only to the cloud server environment.")
        if not self.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY missing. Add it only to the cloud server environment.")

settings=Settings(
    bot_token=os.getenv("BOT_TOKEN","").strip(),
    gemini_api_key=os.getenv("GEMINI_API_KEY","").strip(),
    gemini_model=os.getenv("GEMINI_MODEL","gemini-3.6-flash"),
    database_url=os.getenv("DATABASE_URL","bot_memory.db"),
    reply_probability=max(0.0,min(float(os.getenv("REPLY_PROBABILITY","0.22")),1.0)),
)
