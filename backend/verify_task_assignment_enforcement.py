import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL', 'postgresql://postgres:Password%40123@localhost:5432/kanban_test_db')

async def verify():
    conn = await asyncpg.connect(url)
    
    # 1. Fetch user 1 (Priya Patel) and user 2 (Rohan Gupta)
    priya = await conn.fetchrow("SELECT id FROM users WHERE email = 'priya.patel@techinnovators.com'")
    rohan = await conn.fetchrow("SELECT id FROM users WHERE email = 'rohan.gupta@techinnovators.com'")
    
    priya_id = priya['id']
    rohan_id = rohan['id']

    # Fetch a task assigned to Rohan
    rohan_task = await conn.fetchrow("SELECT id, board_id FROM tasks WHERE assigned_to = $1 LIMIT 1", rohan_id)
    # Fetch a task assigned to Priya
    priya_task = await conn.fetchrow("SELECT id, board_id FROM tasks WHERE assigned_to = $1 LIMIT 1", priya_id)

    # Convert to UUID strings
    def parse_uuid(val):
        import uuid
        return uuid.UUID(f"00000000-0000-0000-0000-{int(val):012d}")

    rohan_uuid = parse_uuid(rohan_id)
    priya_uuid = parse_uuid(priya_id)
    org_id = parse_uuid(1)

    import datetime
    monday = datetime.date(2026, 7, 20)

    ts = await conn.fetchrow("SELECT * FROM fn_create_timesheet($1, $2, $3)", rohan_uuid, org_id, monday)
    ts_id = ts['id']

    # Attempt 1: Rohan logging effort on HIS OWN task -> Should SUCCEED
    try:
        await conn.fetchrow(
            "SELECT * FROM fn_upsert_timesheet_entry($1, $2, $3, $4, $5, $6, $7, $8)",
            ts_id, rohan_uuid, parse_uuid(rohan_task['board_id']), parse_uuid(rohan_task['id']), monday, 8.0, 'task', 'Legitimate effort'
        )
        print("[TEST 1 PASS] Rohan successfully logged effort on task assigned to him!")
    except Exception as e:
        print(f"[TEST 1 FAIL] {e}")

    # Attempt 2: Rohan logging effort on PRIYA'S task -> Should REJECT with TASK_NOT_ASSIGNED
    try:
        await conn.fetchrow(
            "SELECT * FROM fn_upsert_timesheet_entry($1, $2, $3, $4, $5, $6, $7, $8)",
            ts_id, rohan_uuid, parse_uuid(priya_task['board_id']), parse_uuid(priya_task['id']), monday, 8.0, 'task', 'Attempted unauthorized effort'
        )
        print("[TEST 2 FAIL] Database allowed logging time against unassigned task!")
    except Exception as e:
        if "TASK_NOT_ASSIGNED" in str(e):
            print(f"[TEST 2 PASS] Database successfully blocked unassigned task entry: {e}")
        else:
            print(f"[TEST 2 UNEXPECTED ERROR] {e}")

    await conn.close()

if __name__ == '__main__':
    asyncio.run(verify())
