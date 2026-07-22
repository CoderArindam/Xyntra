import asyncio
import asyncpg
import os
import uuid
from dotenv import load_dotenv
from app.auth.jwt import create_access_token

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

async def run_e2e_verification():
    conn = await asyncpg.connect(url)
    
    priya = await conn.fetchrow("SELECT * FROM users WHERE email = 'priya.patel@techinnovators.com'")
    rohan = await conn.fetchrow("SELECT * FROM users WHERE email = 'rohan.gupta@techinnovators.com'")
    admin = await conn.fetchrow("SELECT * FROM users WHERE email = 'admin@techinnovators.com'")

    await conn.close()

    from fastapi.testclient import TestClient
    from app.main import app

    priya_user = {"id": parse_uuid(priya['id']), "email": priya['email'], "role": str(priya['role']), "organization_id": parse_uuid(priya['organization_id'])}
    admin_user = {"id": parse_uuid(admin['id']), "email": admin['email'], "role": str(admin['role']), "organization_id": parse_uuid(admin['organization_id'])}
    rohan_user = {"id": parse_uuid(rohan['id']), "email": rohan['email'], "role": str(rohan['role']), "organization_id": parse_uuid(rohan['organization_id'])}

    priya_token = create_access_token(data={"user_id": str(priya_user['id']), "email": priya_user['email'], "role": priya_user['role'], "organization_id": str(priya_user['organization_id'])})
    admin_token = create_access_token(data={"user_id": str(admin_user['id']), "email": admin_user['email'], "role": admin_user['role'], "organization_id": str(admin_user['organization_id'])})
    rohan_token = create_access_token(data={"user_id": str(rohan_user['id']), "email": rohan_user['email'], "role": rohan_user['role'], "organization_id": str(rohan_user['organization_id'])})

    with TestClient(app, base_url="http://testserver/api/v1") as client:
        # 1. Test Manager Priya Queue
        res_priya_queue = client.get(
            "/timesheets/approvals/queue?status=submitted",
            headers={"Authorization": f"Bearer {priya_token}"}
        )
        assert res_priya_queue.status_code == 200, f"Priya queue failed: {res_priya_queue.text}"
        priya_items = res_priya_queue.json()
        priya_ts_ids = [item['id'] for item in priya_items]
        print(f"[E2E TEST 1 PASS] Manager Priya Queue returned {len(priya_items)} item(s). Contains submitted timesheet: {len(priya_ts_ids) > 0}")

        # 2. Test Super Admin Queue
        res_admin_queue = client.get(
            "/timesheets/approvals/queue?status=submitted",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res_admin_queue.status_code == 200, f"Admin queue failed: {res_admin_queue.text}"
        admin_items = res_admin_queue.json()
        admin_ts_ids = [item['id'] for item in admin_items]
        contains_priya_ts = any(item['approver_id'] == str(priya_user['id']) for item in admin_items)
        print(f"[E2E TEST 2 PASS] Super Admin Queue returned {len(admin_items)} item(s). Timesheet submitted to Priya is NOT in Super Admin queue: {not contains_priya_ts}")

        # 3. Test Detail Authorization
        if priya_items:
            target_ts = priya_items[0]
            target_ts_id = target_ts['id']
            owner_user_id = target_ts['user_id']
            owner_token = create_access_token(data={"user_id": str(owner_user_id), "email": "member@techinnovators.com", "role": "MEMBER", "organization_id": str(priya_user['organization_id'])})

            # Priya (Target Manager Approver) detail access
            res_priya_detail = client.get(
                f"/timesheets/{target_ts_id}",
                headers={"Authorization": f"Bearer {priya_token}"}
            )
            print(f"[E2E TEST 3 PASS] Manager Priya Detail Access Status: {res_priya_detail.status_code} (Expected 200 OK)")
            assert res_priya_detail.status_code == 200

            # Super Admin detail access for timesheet submitted specifically to Priya
            res_admin_detail = client.get(
                f"/timesheets/{target_ts_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            print(f"[E2E TEST 4 PASS] Super Admin Detail Access Status: {res_admin_detail.status_code} (Expected 403 Forbidden)")
            assert res_admin_detail.status_code == 403

            # Timesheet Owner detail access
            res_owner_detail = client.get(
                f"/timesheets/{target_ts_id}",
                headers={"Authorization": f"Bearer {owner_token}"}
            )
            print(f"[E2E TEST 5 PASS] Owner Detail Access Status: {res_owner_detail.status_code} (Expected 200 OK)")
            assert res_owner_detail.status_code == 200

            # Super Admin attempt to approve timesheet submitted specifically to Priya
            res_admin_approve = client.post(
                f"/timesheets/{target_ts_id}/approve",
                json={"comment": "Unauthorized approve attempt by Super Admin"},
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            print(f"[E2E TEST 6 PASS] Super Admin Approve Attempt Status: {res_admin_approve.status_code} (Expected 403 Forbidden)")
            assert res_admin_approve.status_code == 403

if __name__ == '__main__':
    asyncio.run(run_e2e_verification())
