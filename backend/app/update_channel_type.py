import asyncio
from sqlalchemy import text
from app.database import async_session

async def main():
    async with async_session() as db:
        await db.execute(
            text("UPDATE messaging_channels SET type = 'whatsapp' WHERE id = 4")
        )
        await db.commit()
        print("Channel 4 updated to whatsapp")

if __name__ == "__main__":
    asyncio.run(main())
