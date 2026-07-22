import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL', 'postgresql://postgres:Password%40123@localhost:5432/kanban_test_db')

async def diagnose():
    conn = await asyncpg.connect(url)

    # 1. Fetch timesheet 574a4d95-6448-4f78-b4ce-942f3548ecf4
    ts = await conn.fetchrow("SELECT * FROM v_timesheets_canonical WHERE id = '574a4d95-6448-4f78-b4ce-942f3548ecf4'")
    if not ts:
        print("Timesheet 574a4d95-6448-4f78-b4ce-942f3548ecf4 NOT FOUND!")
        # List recent timesheets
        ts_list = await conn.fetch("SELECT id, user_id, submitter_name, week_start_date FROM v_timesheets_canonical ORDER BY created_at DESC LIMIT 5")
        print("Recent timesheets:")
        for r in ts_list:
            print(dict(r))
        await conn.close()
        return

    print("Target Timesheet:", dict(ts))
    owner_user_id = ts['user_id']
    owner_int = owner_user_id.int if hasattr(owner_user_id, 'int') else int(str(owner_user_id).split('-')[-1])
    print(f"Timesheet Owner UUID: {owner_user_id}, Owner Int ID: {owner_int}")

    # Fetch user details
    user = await conn.fetchrow("SELECT id, email, first_name, last_name FROM users WHERE (id::text = $1 OR LTRIM(RIGHT(id::text, 12), '0') = LTRIM(RIGHT($1, 12), '0'))", str(owner_user_id))
    print("User details:", dict(user) if user else "User not found")

    # Fetch tasks assigned to this user
    user_tasks = await conn.fetch("SELECT id, board_id, title, assigned_to FROM tasks WHERE (assigned_to::text = $1 OR LTRIM(RIGHT(assigned_to::text, 12), '0') = LTRIM(RIGHT($1, 12), '0')) LIMIT 10", str(owner_user_id))
    print(f"Tasks assigned to user {user['email'] if user else owner_user_id} (count {len(user_tasks)}):")
    for t in user_tasks:
        print(dict(t))

    await conn.close()

if __name__ == '__main__':
    asyncio.run(diagnose())
