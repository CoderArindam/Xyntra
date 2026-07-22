import asyncio
import asyncpg
import os
import uuid
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

    priya = await conn.fetchrow("SELECT id, email, organization_id FROM users WHERE email = 'priya.patel@techinnovators.com'")
    amit = await conn.fetchrow("SELECT id, email, organization_id FROM users WHERE email = 'amit.kumar@techinnovators.com'")

    priya_uuid = parse_uuid(priya['id'])
    amit_uuid = parse_uuid(amit['id'])
    org_uuid = parse_uuid(priya['organization_id'])

    priya_task = await conn.fetchrow("SELECT id, board_id FROM tasks WHERE assigned_to = $1 LIMIT 1", priya['id'])

    # Clean up any existing timesheet for test week
    import datetime
    monday = datetime.date(2026, 7, 20)
    await conn.execute("DELETE FROM timesheets WHERE (user_id::text = $1 OR LTRIM(RIGHT(user_id::text, 12), '0') = LTRIM(RIGHT($1, 12), '0')) AND week_start_date = $2", str(priya_uuid), monday)

    # Create fresh draft timesheet for Priya
    ts = await conn.fetchrow("SELECT * FROM fn_create_timesheet($1, $2, $3)", priya_uuid, org_uuid, monday)
    ts_id = str(ts['id'])

    # Add entry
    await conn.fetchrow(
        "SELECT * FROM fn_upsert_timesheet_entry($1, $2, $3, $4, $5, $6, $7, $8)",
        uuid.UUID(ts_id), priya_uuid, parse_uuid(priya_task['board_id']), parse_uuid(priya_task['id']), monday, 8.0, 'task', 'Initial work'
    )

    # Submit timesheet to Amit Kumar
    await conn.fetchrow(
        "SELECT * FROM fn_submit_timesheet($1, $2, $3, $4::inet, $5, $6)",
        uuid.UUID(ts_id), priya_uuid, "Submitting for review", '127.0.0.1', 'pytest', amit_uuid
    )

    await conn.close()

    priya_token = create_access_token(data={"user_id": str(priya_uuid), "email": priya['email'], "role": "MANAGER", "organization_id": str(org_uuid)})
    amit_token = create_access_token(data={"user_id": str(amit_uuid), "email": amit['email'], "role": "MANAGER", "organization_id": str(org_uuid)})

    with TestClient(app, base_url="http://testserver/api/v1") as client:
        # Step 1: Verify timesheet is in Amit's submitted queue
        res_submitted_queue = client.get("/timesheets/approvals/queue?status=submitted", headers={"Authorization": f"Bearer {amit_token}"})
        assert res_submitted_queue.status_code == 200
        submitted_ids = [item['id'] for item in res_submitted_queue.json()]
        print(f"[TEST 1 PASS] Amit's submitted queue contains submitted timesheet: {ts_id in submitted_ids}")
        assert ts_id in submitted_ids

        # Step 2: Amit rejects timesheet
        res_reject = client.post(
            f"/timesheets/{ts_id}/reject",
            json={"comment": "Please revise effort hours"},
            headers={"Authorization": f"Bearer {amit_token}"}
        )
        print(f"[TEST 2 PASS] Amit Reject Action Status: {res_reject.status_code} (Expected 200 OK)")
        assert res_reject.status_code == 200
        assert res_reject.json()['status'] == 'rejected'

        # Step 3: Verify rejected timesheet NOW APPEARS in Amit's Rejected Queue
        res_rejected_queue = client.get("/timesheets/approvals/queue?status=rejected", headers={"Authorization": f"Bearer {amit_token}"})
        assert res_rejected_queue.status_code == 200
        rejected_ids = [item['id'] for item in res_rejected_queue.json()]
        print(f"[TEST 3 PASS] Rejected timesheet appears in Amit's Rejected queue: {ts_id in rejected_ids}")
        assert ts_id in rejected_ids, f"Rejected timesheet {ts_id} was NOT found in Amit's rejected queue: {rejected_ids}"

        # Step 4: Verify Priya can edit and re-submit her rejected timesheet
        res_edit = client.post(
            f"/timesheets/{ts_id}/entries",
            json={
                "board_id": str(parse_uuid(priya_task['board_id'])),
                "task_id": str(parse_uuid(priya_task['id'])),
                "entry_date": "2026-07-21",
                "hours": 7.5,
                "entry_type": "task",
                "description": "Revised work"
            },
            headers={"Authorization": f"Bearer {priya_token}"}
        )
        print(f"[TEST 4 PASS] Priya Edit Entry on Rejected Timesheet Status: {res_edit.status_code} (Expected 201 Created)")
        assert res_edit.status_code == 201

        # Step 5: Priya re-submits timesheet to Amit
        res_resubmit = client.post(
            f"/timesheets/{ts_id}/submit",
            json={"member_note": "Re-submitting with revised hours", "approver_id": str(amit_uuid)},
            headers={"Authorization": f"Bearer {priya_token}"}
        )
        print(f"[TEST 5 PASS] Priya Re-submit Action Status: {res_resubmit.status_code} (Expected 200 OK)")
        assert res_resubmit.status_code == 200
        assert res_resubmit.json()['status'] == 'submitted'

    print("ALL REJECT WORKFLOW VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    asyncio.run(run_test())
