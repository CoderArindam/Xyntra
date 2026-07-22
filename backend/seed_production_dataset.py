import asyncio
import asyncpg
import os
import random
import datetime
import uuid
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL', 'postgresql://postgres:Password%40123@localhost:5432/kanban_test_db')

PWD_HASH = '$2b$12$5ZIUXiyEDnVJUWd.qu0/3uGY7tsFX85o.pQi6oOllmXH6radlM5TS'  # 'Password123!'

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

INDIAN_USERS = [
    ("Rajesh", "Sharma", "SUPER_ADMIN", "Executive", "Founder & CEO"),
    ("Priya", "Patel", "MANAGER", "Engineering", "Engineering Lead / Manager"),
    ("Amit", "Kumar", "MANAGER", "DevOps & Infra", "DevOps & Cloud Architect Lead"),
    ("Sneha", "Reddy", "MANAGER", "Design", "Lead UI/UX Designer"),
    ("Aditya", "Singh", "MANAGER", "Product", "Product Manager"),
    ("Neha", "Kapoor", "MANAGER", "QA & Testing", "QA Engineering Manager"),
    
    # Engineers
    ("Rohan", "Gupta", "MEMBER", "Engineering", "Senior Backend Engineer"),
    ("Ananya", "Rao", "MEMBER", "Engineering", "Fullstack Developer"),
    ("Arjun", "Sharma", "MEMBER", "Engineering", "Senior Fullstack Engineer"),
    ("Rohan", "Verma", "MEMBER", "Engineering", "Frontend Engineer"),
    ("Sneha", "Iyer", "MEMBER", "Engineering", "Backend Specialist"),
    ("Vivek", "Rao", "MEMBER", "Engineering", "Systems Architect"),
    ("Rahul", "Das", "MEMBER", "Engineering", "Backend Engineer"),
    ("Aditi", "Mehta", "MEMBER", "Engineering", "Frontend Developer"),
    ("Vikram", "Malhotra", "MEMBER", "Engineering", "Staff Software Engineer"),
    ("Kavya", "Nair", "MEMBER", "Engineering", "Mobile App Engineer"),
    ("Tarun", "Joshi", "MEMBER", "Engineering", "Python AI Engineer"),
    ("Deepa", "Pillai", "MEMBER", "Engineering", "Senior Fullstack Engineer"),
    ("Harish", "Reddy", "MEMBER", "Engineering", "Database Engineer"),
    ("Pooja", "Joshi", "MEMBER", "Engineering", "Backend Engineer"),
    ("Siddharth", "Menon", "MEMBER", "Engineering", "Frontend Developer"),
    ("Meera", "Sen", "MEMBER", "Engineering", "API Architect"),
    ("Rakesh", "Sundaram", "MEMBER", "Engineering", "Microservices Specialist"),
    ("Swati", "Mukherjee", "MEMBER", "Engineering", "Fullstack Developer"),
    ("Manish", "Tripathi", "MEMBER", "Engineering", "Backend Engineer"),
    ("Ishita", "Jain", "MEMBER", "Engineering", "Frontend Specialist"),
    ("Varun", "Varma", "MEMBER", "Engineering", "Senior Software Engineer"),
    ("Preeti", "Deshmukh", "MEMBER", "Engineering", "Backend Engineer"),
    ("Alok", "Agarwal", "MEMBER", "Engineering", "Fullstack Developer"),
    ("Tanvi", "Bhatt", "MEMBER", "Engineering", "Frontend Developer"),
    
    # DevOps & Infra
    ("Nikhil", "Saxena", "MEMBER", "DevOps & Infra", "DevOps Engineer"),
    ("Divya", "Hegde", "MEMBER", "DevOps & Infra", "Site Reliability Engineer"),
    ("Sandeep", "Chhabra", "MEMBER", "DevOps & Infra", "Cloud Security Engineer"),
    ("Ritu", "Kulkarni", "MEMBER", "DevOps & Infra", "Infrastructure Engineer"),
    
    # Design
    ("Abhinav", "Sood", "MEMBER", "Design", "UI/UX Designer"),
    ("Sanya", "Ghosh", "MEMBER", "Design", "Product Designer"),
    ("Gaurav", "Sethi", "MEMBER", "Design", "Visual & Brand Designer"),
    
    # Product & CS
    ("Trisha", "Mahajan", "MEMBER", "Product", "Associate Product Manager"),
    ("Kunal", "Bansal", "MEMBER", "Product", "Technical Product Manager"),
    ("Archana", "Nambiar", "MEMBER", "Product", "Data & Business Analyst"),
    ("Saurabh", "Dave", "MEMBER", "Customer Success", "Customer Success Lead"),
    ("Bhavna", "Grover", "MEMBER", "Customer Success", "Support Engineer"),
    ("Mohit", "Anand", "MEMBER", "Customer Success", "Technical Support Specialist"),
    
    # QA
    ("Shruti", "Iyengar", "MEMBER", "QA & Testing", "Senior QA Automation Engineer"),
    ("Chetan", "Rao", "MEMBER", "QA & Testing", "QA Test Automation Engineer"),
    ("Smita", "Pandey", "MEMBER", "QA & Testing", "Performance & Security Tester"),
    ("Vineet", "Kaushik", "MEMBER", "QA & Testing", "Manual & Mobile QA"),
    ("Priyanka", "Dutta", "MEMBER", "QA & Testing", "QA Automation Engineer"),
    ("Nandan", "Shetty", "MEMBER", "Engineering", "Fullstack Engineer"),
    ("Shreya", "Tiwari", "MEMBER", "Engineering", "Backend Engineer"),
    ("Vishal", "Ahuja", "MEMBER", "Engineering", "Senior Frontend Engineer"),
]

BOARDS_SPEC = [
    ("Razorpay Payment Gateway & UPI Sync", "PAY", "UPI intent flow, Razorpay webhook reconciliation, auto-refunds, and settlement reporting."),
    ("Core Fintech Platform Migration", "FIN", "Migrating monolithic billing engine to event-driven microservices architecture."),
    ("AI Co-Pilot & Customer Analytics", "AI", "LLM-powered customer query assistant and predictive churn analytics pipeline."),
    ("Mobile App V2 (iOS & Android)", "MOB", "React Native rebuild for iOS & Android with offline sync and biometric authentication."),
    ("Admin & Ops Dashboard Revamp", "ADM", "Internal operations portal, manual approval queue, and audit trail viewer."),
    ("Auth & RBAC Security Overhaul", "AUTH", "OAuth2/OIDC provider integration, JWT refresh tokens, and granular permission checks."),
    ("Developer API & Webhook Platform", "API", "Public API gateway, webhook dispatch queue, rate limiting, and developer docs."),
    ("DevOps, CI/CD & Kubernetes Infra", "OPS", "AWS EKS migration, Terraform IAC, Prometheus alerts, and ArgoCD deployment pipelines."),
    ("QA Automation & Regression Suite", "QA", "Cypress E2E testing, Pytest API coverage, and k6 load performance testing."),
    ("Sprint 11 Delivery", "SP11", "Sprint 11 deliverables focusing on UPI v2 SDK and payment failure recovery."),
    ("Sprint 12 Delivery", "SP12", "Sprint 12 deliverables including multi-tenant analytics dashboard and PDF invoice generation."),
    ("Sprint 13 Delivery", "SP13", "Sprint 13 deliverables featuring timesheet approval hierarchy and Slack notifications."),
    ("Bug Fixes & Production Hotfixes", "BUG", "Tracking high-severity production bugs, memory leaks, and customer-reported issues."),
    ("Product Roadmap H2 2026", "RD", "Strategic product initiatives for H2 2026 expansion."),
    ("Customer Feature Requests", "REQ", "Prioritized feature requests from enterprise clients and early adopters."),
]

TASK_TITLES_PER_DOMAIN = {
    "PAY": [
        ("Integrate Razorpay Webhook Callbacks for Auto-Reconciliation", "Handle webhook signatures (X-Razorpay-Signature) and update payment ledger asynchronously when UPI transaction events complete."),
        ("Implement Failover Gateway for Failed UPI Intent Transactions", "If PhonePe or Paytm intent fails twice within 10s, auto-switch fallback route to Razorpay Standard Checkout."),
        ("Fix Refund Status Polling Job Latency in Production", "Replaced polling cron job with webhook events. Refund response time dropped from 45 mins to under 2 seconds."),
        ("Optimize PostgreSQL Query Latency for Payment Ledger", "Add composite indexes on (organization_id, transaction_date) to accelerate ledger audit exports."),
        ("Add Support for WhatsApp UPI QR Code Generation", "Generate dynamic UPI QR codes and dispatch them via WhatsApp Business API."),
        ("Implement Retry Backoff Logic for Webhook Dispatches", "Exponential backoff retry policy for merchant webhook callbacks with dead-letter queue."),
        ("Resolve Double Charge Edge Case on Socket Timeout", "Add idempotency key lock in Redis to prevent concurrent charge execution."),
        ("Audit PCI-DSS Compliance for Card Tokenization Endpoint", "Ensure credit/debit card numbers are never logged in plain text anywhere in application logs."),
    ],
    "FIN": [
        ("Migrate Invoicing Engine to Async Microservice", "Decouple PDF invoice generation from main HTTP worker loop using Celery workers."),
        ("Implement Multi-Currency Tax Rate Calculator", "Add GST/IGST/SGST calculation engine with automatic HSN code lookup."),
        ("Refactor Financial Reconciliation Ledger Service", "Double-entry bookkeeping table structure with strict debit/credit balance constraint."),
        ("Add Real-time Revenue Dashboard Metrics", "Stream completed ledger entries to WebSocket dashboard widget."),
        ("Implement Automated Bank Payout API Integration", "ICICI & HDFC Direct Banking API connection for vendor payouts."),
        ("Build Automated Dispute Resolution Handler", "Allow merchants to upload chargeback evidence directly from dashboard."),
    ],
    "AI": [
        ("Deploy Fine-Tuned Llama-3 Model on vLLM Inference Engine", "Host custom AI model on AWS g5.2xlarge instance with vLLM for sub-200ms latency."),
        ("Implement Retrieval-Augmented Generation (RAG) for Docs", "Chunk product documentation, store vector embeddings in pgvector, and query via cosine distance."),
        ("Build AI Sentiment Analysis Pipeline for Support Tickets", "Classify incoming support tickets as High Priority if negative sentiment score exceeds 0.8."),
        ("Add AI Summarizer for Weekly Manager Reports", "Summarize weekly team performance metrics using AI prompts."),
        ("Optimize Vector Search Latency with HNSW Index", "Add HNSW index on pgvector column in PostgreSQL."),
    ],
    "MOB": [
        ("Implement Biometric Auth (FaceID / Fingerprint) in Mobile App", "Integrate expo-local-authentication for secure PIN-less login."),
        ("Build Offline SQLite Sync Engine for Mobile Timesheets", "Store draft timesheet entries locally in SQLite when offline, sync when connection re-establishes."),
        ("Optimize React Native Navigation Re-rendering", "Memoize expensive list screens and replace ScrollView with FlashList."),
        ("Add Push Notifications for Timesheet Approvals", "Firebase Cloud Messaging (FCM) integration for real-time manager alerts."),
        ("Fix iOS Keyboard Occlusion on Input Fields", "Wrap form layouts in KeyboardAvoidingView with smooth behavior."),
    ],
    "ADM": [
        ("Build Manager Approver Assignment Portal", "UI for assigning department members to global organization approvers."),
        ("Add Export to CSV/Excel for Timesheet Reports", "Stream CSV downloads for organization-wide time logs."),
        ("Implement Audit Trail Viewer for Admin Operations", "Display system activity logs with filterable date range and user ID."),
        ("Fix Pagination Layout Overflow on Small Screens", "Responsive pagination control for table views."),
    ],
    "AUTH": [
        ("Implement JWT Refresh Token Rotation Flow", "Rotate refresh tokens on every refresh call and revoke family on reuse detection."),
        ("Add Multi-Factor Authentication (TOTP / Authenticator App)", "QR code generation and verification for 2FA enrollment."),
        ("Overhaul RBAC Middleware for Organization Isolation", "Strict tenant ID checking across all backend API routes."),
        ("Add Session Revocation Endpoint in User Security Settings", "Allow users to terminate active sessions across devices."),
    ],
    "API": [
        ("Implement Token Bucket Rate Limiting for Public APIs", "Redis-backed rate limiter (100 req/min per API key)."),
        ("Build Developer Portal API Key Generator", "UI for generating and revoking secret API keys with permission scopes."),
        ("Generate OpenAPI 3.0 Documentation & Swagger UI", "Auto-generate interactive API documentation."),
    ],
    "OPS": [
        ("Migrate Backend Workloads to AWS EKS Kubernetes", "Containerize FastAPIs, deploy Helm charts, set up HPA auto-scaling."),
        ("Implement Terraform Infrastructure as Code (IaC)", "Modularize VPC, EKS, RDS PostgreSQL, and Redis infrastructure."),
        ("Set up Prometheus & Grafana Performance Dashboards", "Alertmanager integration for P99 latency spikes > 500ms."),
        ("Automate Database Backup & Point-in-Time Recovery", "Nightly RDS snapshots with S3 lifecycle archival."),
    ],
    "QA": [
        ("Write Cypress End-to-End Test Suite for Timesheet Lifecycle", "Automate draft creation, line item edit, submit, approve, and reject flows."),
        ("Set up Pytest Integration Test Suite in GitHub Actions", "Run API integration tests against ephemeral PostgreSQL container on pull requests."),
        ("Perform k6 Load Testing on Timesheet Submission Endpoint", "Simulate 500 concurrent submissions to verify DB connection pooling."),
    ],
    "SP11": [
        ("Deliver UPI Intent Fallback SDK Version 2.4", "Production release of UPI intent fallback SDK."),
        ("Resolve Payment Status Webhook Race Condition", "Fix timing bug in webhook event processing."),
    ],
    "SP12": [
        ("Build Multi-Tenant Analytics Dashboard Widgets", "Interactive bar charts for team productivity."),
        ("Fix Automated PDF Invoice Currency Symbol Rendering", "Correct INR ₹ symbol encoding in PDF export."),
    ],
    "SP13": [
        ("Implement Organization-wide Timesheet Policy Defaults", "Allow superadmins to configure max daily hours and overtime policies."),
        ("Build Slack Bot Integration for Approver Notifications", "Send interactive Slack message cards for pending timesheets."),
    ],
    "BUG": [
        ("Fix Memory Leak in Websocket Connection Manager", "Unsubscribe dormant socket connections on client disconnect."),
        ("Resolve Null Pointer Exception on Unassigned User Avatar", "Fallback avatar rendering when user avatar_url is null."),
        ("Fix Date Offset Bug in Weekly Timesheet Selector", "Ensure UTC date parsing handles local timezone shifts correctly."),
    ],
    "RD": [
        ("Design Multi-Org Switcher Architecture for Enterprise Clients", "Schema design for multi-tenant users belonging to multiple organizations."),
        ("Plan Enterprise SAML / Single Sign-On (SSO) Integration", "Okta & Azure AD SSO integration roadmap."),
    ],
    "REQ": [
        ("Add Custom Tags and Project Billing Codes to Timesheets", "Allow clients to attach billable tags to line items."),
        ("Implement Manager Bulk Approval Capability", "Approve multiple pending timesheets with a single click."),
    ],
}

async def seed_production_data():
    conn = await asyncpg.connect(url)
    print("Connected to database. Starting rich startup production data generation...")

    async with conn.transaction():
        # 1. Clean existing mock data cleanly
        print("Cleaning up old mock data...")
        await conn.execute("DELETE FROM timesheet_audit_log;")
        await conn.execute("DELETE FROM timesheet_entries;")
        await conn.execute("DELETE FROM timesheets;")
        await conn.execute("DELETE FROM timesheet_approver_assignments;")
        await conn.execute("DELETE FROM notifications;")
        await conn.execute("DELETE FROM activities;")
        await conn.execute("DELETE FROM audit_logs;")
        await conn.execute("DELETE FROM task_proposals;")
        await conn.execute("DELETE FROM meeting_sessions;")
        await conn.execute("DELETE FROM tasks;")
        await conn.execute("DELETE FROM board_columns;")
        await conn.execute("DELETE FROM board_members;")
        await conn.execute("DELETE FROM boards;")
        await conn.execute("DELETE FROM user_preferences;")
        await conn.execute("DELETE FROM users WHERE email != 'placeholder_keep';")
        await conn.execute("DELETE FROM organizations;")

        start_60d = datetime.date.today() - datetime.timedelta(days=90)
        start_ts = datetime.datetime.combine(start_60d, datetime.time(9, 0), tzinfo=datetime.timezone.utc)

        # 2. Insert Organization
        print("Creating Organization: TechInnovators India...")
        org_row = await conn.fetchrow(
            "INSERT INTO organizations (name, created_at) VALUES ($1, $2) RETURNING id",
            "TechInnovators India", start_ts
        )
        org_id_int = org_row['id']
        org_id_uuid = parse_uuid(org_id_int)

        # Ensure Org Policy
        await conn.execute(
            """
            INSERT INTO timesheet_policies (org_id, require_task_link, allow_future_entry, max_hours_per_day, overtime_policy, allow_past_entry_days, submission_deadline_days)
            VALUES ($1, true, false, 12.00, 'flag_only', 90, 999)
            ON CONFLICT (org_id) DO UPDATE SET
              require_task_link = EXCLUDED.require_task_link,
              max_hours_per_day = EXCLUDED.max_hours_per_day,
              allow_past_entry_days = EXCLUDED.allow_past_entry_days,
              submission_deadline_days = 999;
            """,
            org_id_uuid
        )

        # 3. Create 50 Users
        print("Creating 50 realistic startup users...")
        created_users = []
        user_id_map = {} # email -> dict with int & uuid

        for idx, (fname, lname, role, dept, desig) in enumerate(INDIAN_USERS):
            email = "admin@techinnovators.com" if fname == "Rajesh" and lname == "Sharma" else f"{fname.lower()}.{lname.lower()}@techinnovators.com"
            joining_days_ago = random.randint(70, 100)
            user_created = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=joining_days_ago)

            user_row = await conn.fetchrow(
                """
                INSERT INTO users (organization_id, email, password_hash, first_name, last_name, role, is_email_verified, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, true, $7)
                RETURNING id, email, first_name, last_name, role
                """,
                org_id_int, email, PWD_HASH, fname, lname, role, user_created
            )
            u_id_int = user_row['id']
            u_id_uuid = parse_uuid(u_id_int)

            user_info = {
                "id": u_id_int,
                "uuid": u_id_uuid,
                "email": email,
                "first_name": fname,
                "last_name": lname,
                "role": role,
                "dept": dept,
                "desig": desig,
            }
            created_users.append(user_info)
            user_id_map[email] = user_info

        admin_info = user_id_map["admin@techinnovators.com"]
        priya_info = user_id_map["priya.patel@techinnovators.com"]
        amit_info = user_id_map["amit.kumar@techinnovators.com"]
        sneha_info = user_id_map["sneha.reddy@techinnovators.com"]
        aditya_info = user_id_map["aditya.singh@techinnovators.com"]
        neha_info = user_id_map["neha.kapoor@techinnovators.com"]

        managers = [priya_info, amit_info, sneha_info, aditya_info, neha_info]

        # 4. Set up Approver Assignments
        print("Setting up global approver assignments...")
        for mgr in managers:
            await conn.execute(
                """
                INSERT INTO timesheet_approver_assignments (org_id, approver_user_id, assigned_by, is_active)
                VALUES ($1, $2, $3, true)
                ON CONFLICT (org_id, approver_user_id) DO UPDATE SET is_active = true;
                """,
                org_id_uuid, mgr['uuid'], admin_info['uuid']
            )

        # 5. Create Boards & Columns
        print("Creating 15 active projects & boards...")
        created_boards = []
        for name, key, desc in BOARDS_SPEC:
            owner = random.choice([admin_info, priya_info, amit_info, sneha_info, aditya_info])
            b_row = await conn.fetchrow(
                """
                INSERT INTO boards (organization_id, owner_id, name, project_key, description, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, name, project_key
                """,
                org_id_int, owner['id'], name, key, desc, start_ts
            )
            b_id_int = b_row['id']
            b_id_uuid = parse_uuid(b_id_int)

            # Get board columns
            cols = await conn.fetch(
                "SELECT id, column_type, name FROM board_columns WHERE board_id = $1 ORDER BY position",
                b_id_int
            )
            todo_col = next((c['id'] for c in cols if c['column_type'] == 'TODO'), cols[0]['id'])
            prog_col = next((c['id'] for c in cols if c['column_type'] == 'IN_PROGRESS'), cols[0]['id'])
            done_col = next((c['id'] for c in cols if c['column_type'] == 'DONE'), cols[-1]['id'])

            created_boards.append({
                "id": b_id_int,
                "uuid": b_id_uuid,
                "key": key,
                "name": name,
                "todo_col": todo_col,
                "prog_col": prog_col,
                "done_col": done_col,
            })

            # Add board members (all users get access to boards)
            for u in created_users:
                perm = 'OWNER' if u['id'] == owner['id'] else ('EDITOR' if u['role'] in ('MANAGER', 'SUPER_ADMIN') else 'VIEWER')
                await conn.execute(
                    "INSERT INTO board_members (board_id, user_id, permission) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                    b_id_int, u['id'], perm
                )

        # 6. Create ~350 Realistic Tasks
        print("Generating 350+ realistic tasks assigned across the 50 users...")
        user_assigned_tasks = {u['id']: [] for u in created_users}
        total_tasks_created = 0

        for round_idx in range(3):
            for board in created_boards:
                key = board['key']
                domain_tasks = TASK_TITLES_PER_DOMAIN.get(key, TASK_TITLES_PER_DOMAIN['PAY'])
                
                for title_base, desc_base in domain_tasks:
                    if round_idx > 0:
                        title = f"{title_base} (Phase {round_idx + 1})"
                        desc = f"{desc_base} - Iteration {round_idx + 1} for production robustness."
                    else:
                        title = title_base
                        desc = desc_base

                    assignee = random.choice(created_users)
                    creator = random.choice([admin_info, priya_info, amit_info, sneha_info, aditya_info])
                    
                    status_rand = random.random()
                    if status_rand < 0.35:
                        col_id = board['done_col']
                        completed_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=random.randint(2, 40))
                    elif status_rand < 0.75:
                        col_id = board['prog_col']
                        completed_at = None
                    else:
                        col_id = board['todo_col']
                        completed_at = None

                    priority = random.choice(['High', 'Medium', 'Low', 'High', 'Medium'])
                    created_days_ago = random.randint(10, 85)
                    task_created = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=created_days_ago)
                    due_date = task_created + datetime.timedelta(days=random.randint(5, 30))

                    task_row = await conn.fetchrow(
                        """
                        INSERT INTO tasks (board_id, column_id, title, description, priority, assigned_to, created_by, due_date, completed_at, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        RETURNING id, board_id, title
                        """,
                        board['id'], col_id, title, desc, priority, assignee['id'], creator['id'], due_date, completed_at, task_created
                    )

                    t_id_int = task_row['id']
                    t_id_uuid = parse_uuid(t_id_int)

                    t_info = {
                        "id": t_id_int,
                        "uuid": t_id_uuid,
                        "board_id": board['id'],
                        "board_uuid": board['uuid'],
                        "title": title,
                        "key": key
                    }
                    user_assigned_tasks[assignee['id']].append(t_info)
                    total_tasks_created += 1

        print(f"Successfully created {total_tasks_created} tasks across 15 boards!")

        # 7. Generate 3 Months of Historical Timesheets & Entries (~12 Weeks)
        print("Generating 3 months of rich timesheets & approvals...")
        today = datetime.date.today()
        current_monday = today - datetime.timedelta(days=today.weekday())

        mondays = [current_monday - datetime.timedelta(weeks=w) for w in range(12)]
        mondays.reverse()

        total_timesheets = 0
        total_entries = 0

        dept_manager_map = {
            "Engineering": priya_info,
            "DevOps & Infra": amit_info,
            "Design": sneha_info,
            "Product": aditya_info,
            "QA & Testing": neha_info,
            "Customer Success": priya_info,
            "Executive": priya_info
        }

        holiday_dates = {
            current_monday - datetime.timedelta(days=14): "Regional Festival Holiday",
            current_monday - datetime.timedelta(days=42): "National Public Holiday",
        }

        for week_idx, monday in enumerate(mondays):
            is_latest_week = (week_idx == len(mondays) - 1)
            is_second_latest = (week_idx == len(mondays) - 2)

            for u in created_users:
                u_id_uuid = u['uuid']
                target_mgr = dept_manager_map.get(u['dept'], priya_info)
                if u['id'] == target_mgr['id']:
                    target_mgr = admin_info

                target_mgr_uuid = target_mgr['uuid']

                # Create timesheet
                ts_row = await conn.fetchrow(
                    "SELECT * FROM fn_create_timesheet($1, $2, $3)",
                    u_id_uuid, org_id_uuid, monday
                )
                ts_id = parse_uuid(ts_row['id'])
                total_timesheets += 1

                # Workflow status progression & entries
                if is_latest_week:
                    # Keep active current week as a clean, empty DRAFT timesheet for live testing
                    continue

                # Add entries for workdays Mon-Fri (past historical weeks only)
                assigned_ts = user_assigned_tasks.get(u['id'], [])
                for day_offset in range(5):
                    entry_date = monday + datetime.timedelta(days=day_offset)

                    if entry_date > today:
                        continue

                    if entry_date in holiday_dates:
                        await conn.fetchrow(
                            "SELECT * FROM fn_upsert_timesheet_entry($1, $2, $3, $4, $5, $6, $7, $8)",
                            ts_id, u_id_uuid, None, None, entry_date, 8.0, 'holiday', holiday_dates[entry_date]
                        )
                        total_entries += 1
                        continue

                    daily_hours = round(random.choice([7.5, 8.0, 8.0, 8.5, 9.0]), 1)
                    
                    if assigned_ts and random.random() < 0.85:
                        t1 = random.choice(assigned_ts)
                        h1 = 4.0 if daily_hours >= 8.0 else daily_hours
                        await conn.fetchrow(
                            "SELECT * FROM fn_upsert_timesheet_entry($1, $2, $3, $4, $5, $6, $7, $8)",
                            ts_id, u_id_uuid, t1['board_uuid'], t1['uuid'], entry_date, h1, 'task', f"Development and testing on {t1['title']}"
                        )
                        total_entries += 1

                        if daily_hours > 4.0:
                            h2 = daily_hours - h1
                            if len(assigned_ts) > 1 and random.random() < 0.5:
                                t2 = random.choice([t for t in assigned_ts if t['id'] != t1['id']] or [t1])
                                await conn.fetchrow(
                                    "SELECT * FROM fn_upsert_timesheet_entry($1, $2, $3, $4, $5, $6, $7, $8)",
                                    ts_id, u_id_uuid, t2['board_uuid'], t2['uuid'], entry_date, h2, 'task', f"Refactoring and code review for {t2['title']}"
                                )
                            else:
                                await conn.fetchrow(
                                    "SELECT * FROM fn_upsert_timesheet_entry($1, $2, $3, $4, $5, $6, $7, $8)",
                                    ts_id, u_id_uuid, t1['board_uuid'], None, entry_date, h2, 'meeting', "Daily Sprint Standup & Architecture Sync"
                                )
                            total_entries += 1
                    else:
                        await conn.fetchrow(
                            "SELECT * FROM fn_upsert_timesheet_entry($1, $2, $3, $4, $5, $6, $7, $8)",
                            ts_id, u_id_uuid, None, None, entry_date, daily_hours, 'general', "Departmental Planning & Internal Documentation"
                        )
                        total_entries += 1

                # Workflow status progression
                if is_latest_week:
                    if random.random() < 0.4:
                        await conn.fetchrow(
                            "SELECT * FROM fn_submit_timesheet($1, $2, $3, $4::inet, $5, $6)",
                            ts_id, u_id_uuid, f"Week {monday} effort submission for review.", '127.0.0.1', 'Mozilla/5.0', target_mgr_uuid
                        )
                elif is_second_latest:
                    r = random.random()
                    if r < 0.7:
                        await conn.fetchrow(
                            "SELECT * FROM fn_submit_timesheet($1, $2, $3, $4::inet, $5, $6)",
                            ts_id, u_id_uuid, f"Submitting week {monday} timesheet.", '127.0.0.1', 'Mozilla/5.0', target_mgr_uuid
                        )
                        await conn.fetchrow(
                            "SELECT * FROM fn_approve_timesheet($1, $2, $3, $4::inet, $5)",
                            ts_id, target_mgr_uuid, "Approved after verifying effort logs against board tickets.", '127.0.0.1', 'Mozilla/5.0'
                        )
                    elif r < 0.95:
                        await conn.fetchrow(
                            "SELECT * FROM fn_submit_timesheet($1, $2, $3, $4::inet, $5, $6)",
                            ts_id, u_id_uuid, f"Submitting week {monday} timesheet.", '127.0.0.1', 'Mozilla/5.0', target_mgr_uuid
                        )
                else:
                    r = random.random()
                    if r < 0.92:
                        await conn.fetchrow(
                            "SELECT * FROM fn_submit_timesheet($1, $2, $3, $4::inet, $5, $6)",
                            ts_id, u_id_uuid, f"Submitting week {monday} time log.", '127.0.0.1', 'Mozilla/5.0', target_mgr_uuid
                        )
                        await conn.fetchrow(
                            "SELECT * FROM fn_approve_timesheet($1, $2, $3, $4::inet, $5)",
                            ts_id, target_mgr_uuid, "Approved.", '127.0.0.1', 'Mozilla/5.0'
                        )
                    elif r < 0.97:
                        await conn.fetchrow(
                            "SELECT * FROM fn_submit_timesheet($1, $2, $3, $4::inet, $5, $6)",
                            ts_id, u_id_uuid, f"Submitting week {monday} time log.", '127.0.0.1', 'Mozilla/5.0', target_mgr_uuid
                        )
                        await conn.fetchrow(
                            "SELECT * FROM fn_reject_timesheet($1, $2, $3, $4::inet, $5)",
                            ts_id, target_mgr_uuid, "Please add description for Wednesday task entry before approval.", '127.0.0.1', 'Mozilla/5.0'
                        )
                        await conn.fetchrow(
                            "SELECT * FROM fn_submit_timesheet($1, $2, $3, $4::inet, $5, $6)",
                            ts_id, u_id_uuid, "Added missing task entry descriptions as requested.", '127.0.0.1', 'Mozilla/5.0', target_mgr_uuid
                        )
                        await conn.fetchrow(
                            "SELECT * FROM fn_approve_timesheet($1, $2, $3, $4::inet, $5)",
                            ts_id, target_mgr_uuid, "Looks good now. Approved.", '127.0.0.1', 'Mozilla/5.0'
                        )

        print(f"Generated {total_timesheets} timesheets with {total_entries} total time log entries!")
        # 8. Create Notifications via Activities
        print("Generating system notifications...")
        sample_users = created_users[:10]
        for u in sample_users:
            act_row = await conn.fetchrow(
                """
                INSERT INTO activities (organization_id, entity_type, entity_id, user_id, activity_type, old_value, new_value)
                VALUES ($1, 'TASK', 1, $2, 'ASSIGNEE_CHANGED', NULL, jsonb_build_object('assigned_to', $2::int))
                RETURNING id
                """,
                org_id_int, u['id']
            )
            if act_row:
                await conn.execute(
                    "INSERT INTO notifications (user_id, activity_id, is_read) VALUES ($1, $2, false) ON CONFLICT DO NOTHING",
                    u['id'], act_row['id']
                )

    print("=========================================================")
    print("SUCCESS: TechInnovators India production startup dataset successfully seeded!")
    print(f"Users: {len(created_users)} | Boards: {len(created_boards)} | Tasks: {total_tasks_created} | Timesheets: {total_timesheets}")
    print("=========================================================")
    await conn.close()

if __name__ == '__main__':
    asyncio.run(seed_production_data())
