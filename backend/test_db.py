import asyncio
from app.database.connection import db

async def main():
    await db.connect()
    async with db.pool.acquire() as conn:
        boards = await conn.fetch('SELECT id, name, organization_id FROM boards')
        print('\nBoards:')
        for b in boards:
            print(dict(b))
            
        users = await conn.fetch('SELECT id, first_name, last_name, organization_id FROM users WHERE id IN (1, 8, 13)')
        print('\nUsers:')
        for u in users:
            print(dict(u))
    await db.disconnect()

asyncio.run(main())
