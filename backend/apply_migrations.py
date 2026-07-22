import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL', 'postgresql://postgres:Password%40123@localhost:5432/kanban_test_db')

async def main():
    conn = await asyncpg.connect(url)
    with open('../database/migrations/041_timesheet_functions.sql', 'r') as f:
        await conn.execute(f.read())
    print('Applied 041_timesheet_functions.sql')

    with open('../database/migrations/045_simplify_timesheet_approvers.sql', 'r') as f:
        await conn.execute(f.read())
    print('Applied 045_simplify_timesheet_approvers.sql')

    with open('../database/migrations/043_timesheet_views.sql', 'r') as f:
        await conn.execute(f.read())
    print('Applied 043_timesheet_views.sql')

    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
