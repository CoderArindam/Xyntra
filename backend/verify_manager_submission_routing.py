import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL', 'postgresql://postgres:Password%40123@localhost:5432/kanban_test_db')

async def verify():
    conn = await asyncpg.connect(url)

    priya = await conn.fetchrow("SELECT id, email FROM users WHERE email = 'priya.patel@techinnovators.com'")
    amit = await conn.fetchrow("SELECT id, email FROM users WHERE email = 'amit.kumar@techinnovators.com'")

    print(f"Priya ID: {priya['id']}, Amit ID: {amit['id']}")

    # Check approver assignment for Priya
    priya_app = await conn.fetchrow(
        "SELECT * FROM timesheet_approver_assignments WHERE (member_id::text = $1 OR LTRIM(RIGHT(member_id::text, 12), '0') = LTRIM(RIGHT($1, 12), '0'))",
        str(priya['id'])
    )
    print("Priya Approver Assignment in DB:", dict(priya_app) if priya_app else "None configured!")

    # Check submitted timesheets by Priya
    priya_submitted = await conn.fetch(
        "SELECT id, user_id, submitter_name, approver_id, approver_name, status, submitted_at, week_start_date FROM v_timesheets_canonical WHERE (user_id::text = $1 OR LTRIM(RIGHT(user_id::text, 12), '0') = LTRIM(RIGHT($1, 12), '0')) AND status = 'submitted' ORDER BY submitted_at DESC",
        str(priya['id'])
    )
    print(f"Priya Submitted Timesheets ({len(priya_submitted)} found):")
    for row in priya_submitted:
        print(dict(row))

    await conn.close()

if __name__ == '__main__':
    asyncio.run(verify())
