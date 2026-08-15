import database
import asyncio

async def test():
    await database.init_db()


asyncio.run(test())