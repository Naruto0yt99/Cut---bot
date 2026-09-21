from aiogram.enums import ChatMemberStatus

async def is_admin(bot,chat_id,user_id):
    m=await bot.get_chat_member(chat_id,user_id)
    return m.status in {ChatMemberStatus.ADMINISTRATOR,ChatMemberStatus.CREATOR}

async def can_moderate(bot,message):
    if not message.from_user:
        return False
    if not await is_admin(bot,message.chat.id,message.from_user.id):
        return False
    me=await bot.get_chat_member(message.chat.id,bot.id)
    return me.status in {ChatMemberStatus.ADMINISTRATOR,ChatMemberStatus.CREATOR}
