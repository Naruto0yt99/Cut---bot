import os
from dataclasses import dataclass

@dataclass
class Settings:
    bot_token: str
    database_url: str = "bot_memory.db"
    reply_probability: float = 0.22
    bot_username: str = ""

    def __post_init__(self):
        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN missing. Add it only to the server environment or .env.")

settings = Settings(
    bot_token=os.getenv("BOT_TOKEN", ""),
    database_url=os.getenv("DATABASE_URL", "bot_memory.db"),
    reply_probability=float(os.getenv("REPLY_PROBABILITY", "0.22")),
)
