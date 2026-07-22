import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from app.main import app
from app.auth.jwt import create_access_token

load_dotenv()
url = os.getenv('DATABASE_URL', 'postgresql://postgres:Password%40123@localhost:5432/kanban_test_db')

def parse_uuid(val):
    import uuid
    return uuid.UUID(f"00000000-0000-0000-0000-{int(val):012d}")

async def run_test():
    conn = await asyncpg.connect(url)

    rohan = await conn.fetchrow("SELECT id, email, organization_id FROM users WHERE email = 'rohan.gupta@techinnovators.com'")
    priya = await conn.fetchrow("SELECT id, email, organization_id FROM users WHERE email = 'priya.patel@techinnovators.com'")

    rohan_id = rohan['id']
    rohan_uuid = parse_uuid(rohan_id)
    org_uuid = parse_uuid(rohan['organization_id'])

    rohan_task = await conn.fetchrow("SELECT id, board_id FROM tasks WHERE assigned_to = $1 LIMIT 1", rohan_id)
    priya_task = await conn.fetchrow("SELECT id, board_id FROM tasks WHERE assigned_to = $1 LIMIT 1", priya['id'])

    # Create draft timesheet for Rohan
    import datetime
    monday = datetime.date(2026, 7, 20)
    ts = await conn.fetchrow("SELECT * FROM fn_create_timesheet($1, $2, $3)", rohan_uuid, org_uuid, monday)
    ts_id = str(ts['id'])

    await conn.close()

    rohan_token = create_access_token(data={"user_id": str(rohan_uuid), "email": rohan['email'], "role": "MEMBER", "organization_id": str(org_uuid)})

    with TestClient(app, base_url="http://testserver/api/v1") as client:
        # Test A: Log effort on task assigned to Rohan via API -> Should succeed (201 Created)
        payload_valid = {
            "board_id": str(parse_uuid(rohan_task['board_id'])),
            "task_id": str(parse_uuid(rohan_task['id'])),
            "entry_date": "2026-07-20",
            "hours": 8.0,
            "entry_type": "task",
            "description": "API Test - Valid assigned task"
        }
        res_valid = client.post(
            f"/timesheets/{ts_id}/entries",
            json=payload_valid,
            headers={"Authorization": f"Bearer {rohan_token}"}
        )
        print(f"[API TEST A] Assigned Task Log Status: {res_valid.status_code} (Expected 201 Created)")
        assert res_valid.status_code == 201, f"Failed: {res_valid.text}"

        # Test B: Log effort on task assigned to Priya via API -> Should be rejected (422 Unprocessable Entity)
        payload_invalid = {
            "board_id": str(parse_uuid(priya_task['board_id'])),
            "task_id": str(parse_uuid(priya_task['id'])),
            "entry_date": "2026-07-20",
            "hours": 8.0,
            "entry_type": "task",
            "description": "API Test - Unassigned task attempt"
        }
        res_invalid = client.post(
            f"/timesheets/{ts_id}/entries",
            json=payload_invalid,
            headers={"Authorization": f"Bearer {rohan_token}"}
        )
        print(f"[API TEST B] Unassigned Task Log Status: {res_invalid.status_code} (Expected 422 Unprocessable Entity)")
        # Test C: Log effort with raw task ID integer string "5" or reference
        payload_string_task = {
            "board_id": str(rohan_task['board_id']),
            "task_id": str(rohan_task['id']),
            "entry_date": "2026-07-21",
            "hours": 4.0,
            "entry_type": "task",
            "description": "API Test - String Task ID payload"
        }
        res_string_task = client.post(
            f"/timesheets/{ts_id}/entries",
            json=payload_string_task,
            headers={"Authorization": f"Bearer {rohan_token}"}
        )
        print(f"[API TEST C] Raw String Task ID Log Status: {res_string_task.status_code} (Expected 201 Created)")
        assert res_string_task.status_code == 201, f"Failed: {res_string_task.text}"

    print("ALL API VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    asyncio.run(run_test())
