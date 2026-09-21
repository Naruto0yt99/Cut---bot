from aiogram import Bot

async def get_pack_stickers(bot:Bot, set_name:str):
    if not set_name:
        return []
    pack=await bot.get_sticker_set(set_name)
    return pack.stickers
