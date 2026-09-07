import asyncio
from app.database import async_session
from sqlalchemy import select
from app.models.messaging_channel import MessagingChannel

async def check_channel():
    async with async_session() as db:
        result = await db.execute(select(MessagingChannel).where(MessagingChannel.id == 5))
        c = result.scalar_one_or_none()
        if c:
            print(f"Channel {c.id}: type={c.type}")
        else:
            print("Channel 5 not found!")

if __name__ == "__main__":
    asyncio.run(check_channel())
