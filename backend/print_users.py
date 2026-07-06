import asyncio
import asyncpg
from app.config.config import settings

async def main():
    conn = await asyncpg.connect(settings.DATABASE_URL)
    users = await conn.fetch("SELECT id, email, role FROM users LIMIT 5")
    for u in users:
        print(dict(u))
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
