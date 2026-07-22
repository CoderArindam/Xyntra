import asyncio
import asyncpg
import os
import uuid
import datetime
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL', 'postgresql://postgres:Password%40123@localhost:5432/kanban_test_db')

def parse_uuid(val):
    if val is None:
        return None
    if isinstance(val, uuid.UUID):
        return val
    s_val = str(val).strip()
    if s_val.isdigit():
        return uuid.UUID(f"00000000-0000-0000-0000-{int(s_val):012d}")
    try:
        return uuid.UUID(s_val)
    except Exception:
        return None

async def seed():
    conn = await asyncpg.connect(url)
    
    priya = await conn.fetchrow("SELECT * FROM users WHERE email = 'priya.patel@techinnovators.com'")
    rohan = await conn.fetchrow("SELECT * FROM users WHERE email = 'rohan.gupta@techinnovators.com'")
    admin = await conn.fetchrow("SELECT * FROM users WHERE email = 'admin@techinnovators.com'")
    
    priya_id = parse_uuid(priya['id'])
    rohan_id = parse_uuid(rohan['id'])
    admin_id = parse_uuid(admin['id'])
    org_id = parse_uuid(priya['organization_id'])

    # Ensure a board exists for org_id
    board = await conn.fetchrow("SELECT id FROM boards WHERE (organization_id::text = $1 OR LTRIM(RIGHT(organization_id::text, 12), '0') = LTRIM(RIGHT($1, 12), '0')) LIMIT 1", str(org_id))
    if not board:
        board = await conn.fetchrow(
            "INSERT INTO boards (name, organization_id, created_by) VALUES ($1, $2, $3) RETURNING id",
            'Core Engineering Board', org_id, admin_id
        )
    board_id = parse_uuid(board['id'])

    week_start = datetime.date(2026, 7, 20)

    # 1. Create timesheet for Rohan
    ts_row = await conn.fetchrow(
        "SELECT * FROM fn_create_timesheet($1, $2, $3)",
        rohan_id, org_id, week_start
    )
    ts_id = parse_uuid(ts_row['id'])

    # 2. Upsert entry for Rohan
    await conn.fetchrow(
        "SELECT * FROM fn_upsert_timesheet_entry($1, $2, $3, $4, $5, $6, $7, $8)",
        ts_id, rohan_id, board_id, None, week_start, 8.0, 'general', 'Backend Optimization for UPI Gateway'
    )

    # 3. Submit Rohan's timesheet specifically to Priya Patel (Manager)
    submitted_ts = await conn.fetchrow(
        "SELECT * FROM fn_submit_timesheet($1, $2, $3, $4::inet, $5, $6)",
        ts_id, rohan_id, 'Please review my week 2026-07-20 effort', '127.0.0.1', 'Seed Script', priya_id
    )

    print(f"SEEDED SUCCESS: Timesheet {ts_id} submitted by Rohan Gupta -> Target Approver: Priya Patel (Manager). Status: {submitted_ts['status']}")
    await conn.close()

if __name__ == '__main__':
    asyncio.run(seed())
