import asyncio
from app.database.connection import db
from app.services.user_service import UserService

async def main():
    await db.connect()
    async with db.pool.acquire() as conn:
        svc = UserService(conn)
        users = await svc.get_all_users({"organization_id": 3})
        print(type(users[0]))
        print(users[0])
        try:
            print(users[0].first_name)
        except Exception as e:
            print("Error accessing first_name:", type(e), e)
    await db.disconnect()

asyncio.run(main())
