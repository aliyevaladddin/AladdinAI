import asyncio
from app.database import async_session
from sqlalchemy import select
from app.models.messaging_channel import MessagingChannel

async def check_channel():
    async with async_session() as db:
        result = await db.execute(select(MessagingChannel).where(MessagingChannel.id == 5))
        c = result.scalar_one_or_none()
        if c:
            has_secret = bool(c.webhook_secret)
            secret_status = "set" if has_secret else "not_set"
            print(f"Channel {c.id}: type={c.type}, secret_status={secret_status}")
        else:
            print("Channel 5 not found!")

if __name__ == "__main__":
    asyncio.run(check_channel())
