# KAIO — Enterprise Timesheet Feature

## Phased Implementation Plan & Gemini 2.0 Flash Prompts

> **Architecture Contract (read before every phase)**
>
> - NO inline SQL in Python. All reads use `v_*_canonical` views. All writes call `fn_*` stored procedures.
> - RBAC roles: `superadmin` > `manager` > `member` (three roles only — no viewer role exists)
> - **Manager visibility rule**: A manager can only see, approve, or report on timesheets that contain entries logged against boards they are explicitly assigned as approver on. A manager has NO access to timesheets from boards they are not assigned to. Only `superadmin` has org-wide visibility.
> - Migrations continue sequentially from `036_*.sql`
> - All new API routes live under `/api/v1/timesheets`
> - Every new router follows the existing FastAPI pattern in `backend/app/routers/`

---

## Feature Overview

The KAIO Timesheet system is a fully configurable, enterprise-grade effort-tracking module built on top of the existing Kanban + Meeting infrastructure. It supports:

- **Organization-level policy configuration** (week start/end, working hours, overtime rules, lockout windows)
- **Per-project approver assignment** (Superadmin assigns which manager approves which board/project)
- **Weekly timesheet submission by members**
- **Multi-stage approval workflows** (Submit → Review → Approved / Recalled / Rejected)
- **Rich audit trail** integrated with the existing `security_events` and `activity` tables
- **Notification deep-linking** into the existing notification system
- **RBAC-gated UI** matching the existing `isManagerOrAdmin` pattern

---

## Phase Architecture Map

```
Phase 1  ─── Database Foundation (Migrations 036–042)
Phase 2  ─── Backend: Config & Policy APIs
Phase 3  ─── Backend: Timesheet CRUD & Submission APIs
Phase 4  ─── Backend: Approval Workflow APIs
Phase 5  ─── Frontend: Admin Configuration UI
Phase 6  ─── Frontend: Member Timesheet Entry UI
Phase 7  ─── Frontend: Manager Approval UI
Phase 8  ─── Notifications, Audit Trail & Reports
Phase 9   ─── Hardening, Edge Cases & Integration Tests
Phase 9.5 ─── End-to-End Real-Life Debug, Stress & Edge Case Test Phase
Phase 10  ─── Tempo-Style Calendar View & Daily Worklog Experience
```

---

## Phase 1 — Database Foundation

**Migrations: `036_timesheet_enums.sql` → `042_timesheet_views.sql`**

New tables introduced:

- `timesheet_policies` — org-level week config, working hours, lockout rules
- `timesheet_approver_assignments` — maps board_id → approver user_id
- `timesheets` — weekly timesheet header (user, week_start_date, status, submitted_at, etc.)
- `timesheet_entries` — individual day+task log lines (board_id, task_id, date, hours, note)
- `timesheet_audit_log` — every status transition with actor, timestamp, comment
- `timesheet_recall_requests` — member-initiated recall after submission

New views:

- `v_timesheets_canonical` — timesheet header + submitter + approver + policy context
- `v_timesheet_entries_canonical` — entry lines with task/board resolution
- `v_timesheet_audit_canonical` — full audit trail per timesheet
- `v_timesheet_policy_canonical` — org policy with computed week boundaries

New stored functions:

- `fn_upsert_timesheet_policy(...)` — create/update org policy
- `fn_assign_timesheet_approver(board_id, approver_user_id, assigned_by)` — approver mapping
- `fn_create_timesheet(user_id, org_id, week_start_date)` — open a new weekly timesheet
- `fn_upsert_timesheet_entry(timesheet_id, task_id, board_id, date, hours, note)` — log/update entry
- `fn_delete_timesheet_entry(entry_id, user_id)` — remove entry (only while DRAFT)
- `fn_submit_timesheet(timesheet_id, user_id)` — transition DRAFT → SUBMITTED
- `fn_approve_timesheet(timesheet_id, approver_id, comment)` — SUBMITTED → APPROVED
- `fn_reject_timesheet(timesheet_id, approver_id, comment)` — SUBMITTED → REJECTED
- `fn_recall_timesheet(timesheet_id, user_id, reason)` — SUBMITTED → RECALLED
- `fn_check_timesheet_approver_access(user_id, timesheet_id)` — RBAC guard for approvers

---

### PROMPT 1 — Database Foundation

```
You are a senior PostgreSQL architect working on KAIO, an enterprise Kanban + AI meeting platform.

## Existing Context
- PostgreSQL 15+
- Migrations run from 001 to 035. Your migrations start at 036.
- Existing enums in 002_enums.sql: user_role, task_priority, task_status, session_status
- Core tables: organizations, users, boards, tasks, comments, notifications, active_sessions, security_events
- Architecture rule: ALL reads via v_*_canonical views. ALL writes via fn_* stored procedures. Zero raw SQL in application code.
- uuid-ossp and pgcrypto extensions already enabled.

## Feature to Build
Enterprise Timesheet System. Generate 7 migration files:

### 036_timesheet_enums.sql
Add these PostgreSQL enums:
- timesheet_status: 'draft', 'submitted', 'approved', 'rejected', 'recalled'
- timesheet_entry_type: 'task', 'meeting', 'general', 'leave', 'holiday'
- week_start_day: 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'
- overtime_policy: 'none', 'flag_only', 'block_submission'

### 037_timesheet_policy_schema.sql
Table: timesheet_policies (one row per org, upsertable)
- id UUID PK DEFAULT uuid_generate_v4()
- org_id UUID FK → organizations(id) UNIQUE NOT NULL
- week_start_day week_start_day NOT NULL DEFAULT 'monday'
- standard_hours_per_day NUMERIC(4,2) NOT NULL DEFAULT 8.0
- standard_hours_per_week NUMERIC(5,2) NOT NULL DEFAULT 40.0
- max_hours_per_day NUMERIC(4,2) DEFAULT 12.0
- overtime_policy overtime_policy NOT NULL DEFAULT 'flag_only'
- submission_deadline_days INTEGER DEFAULT 2 (days after week end to submit)
- allow_future_entry BOOLEAN DEFAULT false
- allow_past_entry_days INTEGER DEFAULT 30
- require_task_link BOOLEAN DEFAULT false (force every entry to link a task)
- allow_member_recall BOOLEAN DEFAULT true
- created_at TIMESTAMPTZ DEFAULT NOW()
- updated_at TIMESTAMPTZ DEFAULT NOW()

Table: timesheet_approver_assignments
- id UUID PK
- org_id UUID FK → organizations(id)
- board_id UUID FK → boards(id) NULLABLE (null = org-level fallback approver)
- approver_user_id UUID FK → users(id)
- assigned_by UUID FK → users(id)
- is_active BOOLEAN DEFAULT true
- created_at TIMESTAMPTZ DEFAULT NOW()
- UNIQUE(org_id, board_id, approver_user_id)

### 038_timesheet_core_schema.sql
Table: timesheets (weekly header)
- id UUID PK DEFAULT uuid_generate_v4()
- org_id UUID FK → organizations(id) NOT NULL
- user_id UUID FK → users(id) NOT NULL
- week_start_date DATE NOT NULL (always normalized to policy week_start_day)
- week_end_date DATE NOT NULL (computed: week_start_date + 6 days)
- status timesheet_status NOT NULL DEFAULT 'draft'
- total_hours NUMERIC(6,2) GENERATED ALWAYS AS (computed from entries) STORED — actually store as computed column updated by trigger
- submitted_at TIMESTAMPTZ
- reviewed_at TIMESTAMPTZ
- approver_id UUID FK → users(id) NULLABLE
- approver_comment TEXT
- member_note TEXT (optional note on submission)
- created_at TIMESTAMPTZ DEFAULT NOW()
- updated_at TIMESTAMPTZ DEFAULT NOW()
- UNIQUE(org_id, user_id, week_start_date)

Table: timesheet_entries (daily log lines)
- id UUID PK DEFAULT uuid_generate_v4()
- timesheet_id UUID FK → timesheets(id) ON DELETE CASCADE
- user_id UUID FK → users(id) NOT NULL
- board_id UUID FK → boards(id) NULLABLE
- task_id UUID FK → tasks(id) NULLABLE
- entry_date DATE NOT NULL
- hours NUMERIC(4,2) NOT NULL CHECK(hours > 0 AND hours <= 24)
- entry_type timesheet_entry_type NOT NULL DEFAULT 'task'
- description TEXT
- is_overtime BOOLEAN DEFAULT false
- created_at TIMESTAMPTZ DEFAULT NOW()
- updated_at TIMESTAMPTZ DEFAULT NOW()

Table: timesheet_audit_log
- id UUID PK DEFAULT uuid_generate_v4()
- timesheet_id UUID FK → timesheets(id)
- actor_user_id UUID FK → users(id)
- from_status timesheet_status
- to_status timesheet_status NOT NULL
- comment TEXT
- ip_address INET
- user_agent TEXT
- created_at TIMESTAMPTZ DEFAULT NOW()

### 039_timesheet_indexes.sql
Create indexes on:
- timesheets(org_id, user_id, week_start_date)
- timesheets(org_id, status)
- timesheets(approver_id, status) WHERE approver_id IS NOT NULL
- timesheet_entries(timesheet_id)
- timesheet_entries(user_id, entry_date)
- timesheet_entries(board_id) WHERE board_id IS NOT NULL
- timesheet_entries(task_id) WHERE task_id IS NOT NULL
- timesheet_audit_log(timesheet_id)
- timesheet_approver_assignments(org_id, board_id)

### 040_timesheet_functions.sql
Write ALL of these PL/pgSQL stored functions:

fn_upsert_timesheet_policy(p_org_id, p_week_start_day, p_std_hours_day, p_std_hours_week, p_max_hours_day, p_overtime_policy, p_submission_deadline_days, p_allow_future_entry, p_allow_past_entry_days, p_require_task_link, p_allow_member_recall, p_actor_user_id)
→ Upserts policy row, validates actor is superadmin in org, returns policy record.

fn_assign_timesheet_approver(p_org_id, p_board_id, p_approver_user_id, p_assigned_by)
→ Validates assigned_by is superadmin, validates approver is manager/superadmin in org, upserts assignment, deactivates old assignment for same board if exists.

fn_remove_timesheet_approver(p_assignment_id, p_actor_user_id)
→ Sets is_active=false. Validates actor is superadmin.

fn_create_timesheet(p_user_id, p_org_id, p_week_start_date)
→ Normalizes week_start_date to nearest policy week_start_day, computes week_end_date, inserts timesheet with status=draft. Raises conflict if already exists.

fn_upsert_timesheet_entry(p_timesheet_id, p_user_id, p_board_id, p_task_id, p_entry_date, p_hours, p_entry_type, p_description)
→ Validates timesheet status is 'draft'. Validates entry_date is within week boundaries. Validates hours constraints from policy. Validates if require_task_link then task_id must be set. Flags is_overtime if entry pushes day total > policy max_hours_per_day. Upserts entry row. Recalculates and updates timesheets.total_hours.

fn_delete_timesheet_entry(p_entry_id, p_user_id)
→ Only allowed when timesheet status = 'draft'. Deletes entry. Recalculates total_hours.

fn_submit_timesheet(p_timesheet_id, p_user_id, p_member_note, p_ip_address, p_user_agent)
→ Validates status = 'draft'. Validates submission_deadline not exceeded. Validates minimum hours if policy requires. Resolves approver: look up timesheet_approver_assignments for the specific boards referenced in this timesheet's entries — if a board-specific assignment exists, use that approver; if multiple boards have different approvers raise EXCEPTION 'MULTIPLE_APPROVERS_CONFLICT' (superadmin must resolve); if no board-specific assignment, fall back to the org-level (board_id IS NULL) approver; if neither exists, set approver_id=NULL and raise soft warning 'NO_APPROVER_CONFIGURED'. Sets approver_id, status='submitted', submitted_at=NOW(). Inserts audit log row. Triggers notification to approver.

fn_get_manager_accessible_timesheet_ids(p_manager_id, p_org_id) RETURNS SETOF UUID
→ Returns the set of timesheet IDs visible to a given manager: SELECT DISTINCT t.id FROM timesheets t JOIN timesheet_entries e ON e.timesheet_id = t.id JOIN timesheet_approver_assignments taa ON taa.board_id = e.board_id WHERE taa.approver_user_id = p_manager_id AND taa.org_id = p_org_id AND taa.is_active = true AND t.org_id = p_org_id. Also includes timesheets where taa.board_id IS NULL (org-level fallback) only if no board-specific approver exists for any entry in that timesheet. This function is the single source of truth for all manager-scoped list queries.

fn_approve_timesheet(p_timesheet_id, p_approver_id, p_comment, p_ip_address, p_user_agent)
→ Calls fn_check_timesheet_approver_access. Sets status='approved', reviewed_at=NOW(), approver_comment. Inserts audit log. Triggers notification to submitter.

fn_reject_timesheet(p_timesheet_id, p_approver_id, p_comment, p_ip_address, p_user_agent)
→ Same as approve but status='rejected'. Rejected timesheets revert to draft so member can edit and resubmit. Updates status='draft', clears submitted_at, sets approver_comment. Inserts audit log. Notifies submitter.

fn_recall_timesheet(p_timesheet_id, p_user_id, p_reason, p_ip_address, p_user_agent)
→ Validates policy.allow_member_recall=true. Validates status='submitted'. Sets status='draft'. Inserts audit log. Notifies approver.

fn_check_timesheet_approver_access(p_user_id, p_timesheet_id) RETURNS BOOLEAN
→ Returns true ONLY IF: (a) the user is a superadmin in the org, OR (b) the user is the explicitly assigned approver for at least one board that appears in the timesheet's entries, OR (c) the user is the org-level fallback approver (board_id IS NULL assignment) AND no board-specific approver exists for that timesheet.
→ A manager who has no approver assignment for any board in the timesheet MUST return false. Being a manager in the org is NOT sufficient — assignment is required.

fn_get_manager_accessible_timesheet_ids(p_manager_id, p_org_id) RETURNS SETOF UUID
→ Returns the set of timesheet IDs the given manager is permitted to see: timesheets whose entries include at least one board_id for which the manager has an active assignment in timesheet_approver_assignments. Used to scope all manager list queries.

### 041_timesheet_triggers.sql
- updated_at trigger on timesheets and timesheet_entries
- After INSERT/UPDATE/DELETE on timesheet_entries: recalculate timesheets.total_hours for parent timesheet_id

### 042_timesheet_views.sql
v_timesheets_canonical:
SELECT t.*,
  u.display_name AS submitter_name, u.email AS submitter_email,
  a.display_name AS approver_name, a.email AS approver_email,
  p.week_start_day, p.standard_hours_per_week, p.standard_hours_per_day,
  p.overtime_policy, p.allow_member_recall,
  COUNT(e.id) AS entry_count
FROM timesheets t
JOIN users u ON u.id = t.user_id
LEFT JOIN users a ON a.id = t.approver_id
LEFT JOIN timesheet_policies p ON p.org_id = t.org_id
LEFT JOIN timesheet_entries e ON e.timesheet_id = t.id
GROUP BY t.id, u.display_name, u.email, a.display_name, a.email, p.week_start_day, p.standard_hours_per_week, p.standard_hours_per_day, p.overtime_policy, p.allow_member_recall

v_timesheet_entries_canonical:
SELECT e.*,
  b.name AS board_name,
  tk.title AS task_title,
  t.week_start_date, t.week_end_date, t.status AS timesheet_status
FROM timesheet_entries e
JOIN timesheets t ON t.id = e.timesheet_id
LEFT JOIN boards b ON b.id = e.board_id
LEFT JOIN tasks tk ON tk.id = e.task_id

v_timesheet_audit_canonical:
SELECT ta.*,
  u.display_name AS actor_name, u.email AS actor_email,
  t.user_id AS owner_user_id, t.week_start_date
FROM timesheet_audit_log ta
JOIN users u ON u.id = ta.actor_user_id
JOIN timesheets t ON t.id = ta.timesheet_id

v_timesheet_approver_assignments_canonical:
SELECT taa.*,
  u.display_name AS approver_name, u.email AS approver_email,
  b.name AS board_name,
  ab.display_name AS assigned_by_name
FROM timesheet_approver_assignments taa
JOIN users u ON u.id = taa.approver_user_id
LEFT JOIN boards b ON b.id = taa.board_id
JOIN users ab ON ab.id = taa.assigned_by
WHERE taa.is_active = true

v_timesheet_policy_canonical:
SELECT tp.*, o.name AS org_name, o.slug AS org_slug
FROM timesheet_policies tp
JOIN organizations o ON o.id = tp.org_id

Output each migration as a clearly labelled SQL code block. Use PL/pgSQL for all functions. Add inline comments explaining business logic inside functions. Never use raw SELECT/INSERT/UPDATE/DELETE outside of stored functions and views.
```

---

## Phase 2 — Backend: Config & Policy APIs

**New file:** `backend/app/routers/timesheet_admin.py`
**New file:** `backend/app/schemas/timesheet_admin.py`

Endpoints:

- `GET /api/v1/timesheets/policy` — fetch org policy
- `PUT /api/v1/timesheets/policy` — upsert org policy (superadmin only)
- `GET /api/v1/timesheets/approvers` — list all approver assignments for org
- `POST /api/v1/timesheets/approvers` — assign approver to board
- `DELETE /api/v1/timesheets/approvers/{assignment_id}` — remove approver assignment
- `GET /api/v1/timesheets/approvers/eligible` — list users eligible to be approvers (managers + superadmins)

---

### PROMPT 2 — Backend: Config & Policy APIs

```
You are a senior Python/FastAPI engineer working on KAIO.

## Architecture Rules (NON-NEGOTIABLE)
- NEVER write raw SQL (SELECT/INSERT/UPDATE/DELETE) in Python files.
- ALL reads: SELECT * FROM v_*_canonical WHERE ...
- ALL writes: SELECT * FROM fn_*(...) (called via asyncpg)
- Auth: extract current_user from existing JWT dependency `get_current_user`
- RBAC: check user role from current_user claims. Superadmin = role 'superadmin'. Use HTTP 403 for unauthorized.
- Pydantic v2 for all schemas.
- asyncpg for all DB calls via `get_db_connection()` dependency.
- Follow the exact pattern in backend/app/routers/task_proposals.py for router structure.
- Error responses use the standard format: {"detail": "...", "error_code": "...", "timestamp": "..."}

## Task
Create two files:

### File 1: backend/app/schemas/timesheet_admin.py
Pydantic v2 models:

TimesheetPolicyResponse:
- org_id: UUID
- week_start_day: Literal['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
- standard_hours_per_day: float
- standard_hours_per_week: float
- max_hours_per_day: float
- overtime_policy: Literal['none','flag_only','block_submission']
- submission_deadline_days: int
- allow_future_entry: bool
- allow_past_entry_days: int
- require_task_link: bool
- allow_member_recall: bool
- org_name: str
- org_slug: str

TimesheetPolicyUpdateRequest:
- week_start_day: Optional[...]
- standard_hours_per_day: Optional[float] with Field(ge=0.5, le=24)
- standard_hours_per_week: Optional[float] with Field(ge=1, le=168)
- max_hours_per_day: Optional[float] with Field(ge=1, le=24)
- overtime_policy: Optional[...]
- submission_deadline_days: Optional[int] with Field(ge=0, le=30)
- allow_future_entry: Optional[bool]
- allow_past_entry_days: Optional[int] with Field(ge=0, le=365)
- require_task_link: Optional[bool]
- allow_member_recall: Optional[bool]

ApproverAssignmentResponse:
- id: UUID
- org_id: UUID
- board_id: Optional[UUID]
- board_name: Optional[str]
- approver_user_id: UUID
- approver_name: str
- approver_email: str
- assigned_by_name: str

AssignApproverRequest:
- board_id: Optional[UUID] = None (null = org-level fallback)
- approver_user_id: UUID

EligibleApproverResponse:
- user_id: UUID
- display_name: str
- email: str
- role: str

### File 2: backend/app/routers/timesheet_admin.py
FastAPI APIRouter with prefix="/timesheets" and tags=["Timesheet Admin"]

Implement these endpoints:

GET /policy
→ Requires Bearer auth. Any authenticated org member can read policy.
→ SELECT * FROM v_timesheet_policy_canonical WHERE org_id = $1
→ Returns TimesheetPolicyResponse. If no policy exists return sensible defaults.

PUT /policy
→ Requires superadmin role. 403 if not.
→ Validate request body with TimesheetPolicyUpdateRequest.
→ Call SELECT * FROM fn_upsert_timesheet_policy($1,$2,...) with all fields merged with existing policy.
→ Returns updated TimesheetPolicyResponse.

GET /approvers
→ Requires superadmin or manager role. 403 if member.
→ SELECT * FROM v_timesheet_approver_assignments_canonical WHERE org_id = $1 ORDER BY board_name NULLS FIRST
→ Returns List[ApproverAssignmentResponse]

GET /approvers/eligible
→ Requires superadmin role. 403 if manager or member.
→ SELECT * FROM v_users_canonical WHERE org_id = $1 AND role IN ('superadmin', 'manager') ORDER BY display_name
→ Only superadmins and managers are eligible to be approvers. Members cannot be assigned as approvers.
→ Returns List[EligibleApproverResponse]

POST /approvers
→ Requires superadmin role.
→ Validate AssignApproverRequest.
→ Call SELECT * FROM fn_assign_timesheet_approver($1,$2,$3,$4)
→ Returns ApproverAssignmentResponse with 201 status.

DELETE /approvers/{assignment_id}
→ Requires superadmin role.
→ Call SELECT fn_remove_timesheet_approver($1, $2)
→ Returns 204 No Content.

Register this router in backend/app/main.py by adding:
from app.routers import timesheet_admin
app.include_router(timesheet_admin.router, prefix="/api/v1")

Show the exact import line and include_router line to add to main.py. Do not rewrite main.py, just show the two lines to insert.
```

---

## Phase 3 — Backend: Timesheet CRUD & Submission APIs

**New file:** `backend/app/routers/timesheets.py`
**New file:** `backend/app/schemas/timesheets.py`

Endpoints:
GET /api/v1/timesheets

Member

- own timesheets only

Manager

- only timesheets containing boards they are explicitly assigned to approve

Superadmin

- all organization timesheets
- `POST /api/v1/timesheets` — create new weekly timesheet
- `GET /api/v1/timesheets/{id}` — fetch timesheet detail + entries
- `POST /api/v1/timesheets/{id}/entries` — add/update entry
- `DELETE /api/v1/timesheets/{id}/entries/{entry_id}` — remove entry
- `POST /api/v1/timesheets/{id}/submit` — submit for approval
- `POST /api/v1/timesheets/{id}/recall` — recall a submitted timesheet
- `GET /api/v1/timesheets/calendar` — fetch aggregated daily worklogs and capacity for calendar view

---

### PROMPT 3 — Backend: Timesheet CRUD & Submission APIs

```
You are a senior Python/FastAPI engineer working on KAIO.

## Architecture Rules (NON-NEGOTIABLE)
- NEVER write raw SQL in Python.
- All reads: SELECT * FROM v_*_canonical
- All writes: SELECT * FROM fn_*(...)
- Pydantic v2. asyncpg. get_current_user dependency. get_db_connection dependency.
- Standard error format: {"detail": "...", "error_code": "...", "timestamp": "..."}
- Extract request IP from Request object: request.client.host
- Extract user agent from request headers: request.headers.get("user-agent", "")

## Task
Create two files:

### File 1: backend/app/schemas/timesheets.py

TimesheetResponse:
- id: UUID
- org_id: UUID
- user_id: UUID
- submitter_name: str
- submitter_email: str
- week_start_date: date
- week_end_date: date
- status: str
- total_hours: float
- standard_hours_per_week: float (from policy join in view)
- entry_count: int
- submitted_at: Optional[datetime]
- reviewed_at: Optional[datetime]
- approver_id: Optional[UUID]
- approver_name: Optional[str]
- approver_comment: Optional[str]
- member_note: Optional[str]

TimesheetDetailResponse(TimesheetResponse):
- entries: List[TimesheetEntryResponse]
- audit_log: List[TimesheetAuditResponse]

TimesheetEntryResponse:
- id: UUID
- timesheet_id: UUID
- board_id: Optional[UUID]
- board_name: Optional[str]
- task_id: Optional[UUID]
- task_title: Optional[str]
- entry_date: date
- hours: float
- entry_type: str
- description: Optional[str]
- is_overtime: bool

TimesheetAuditResponse:
- id: UUID
- actor_name: str
- actor_email: str
- from_status: Optional[str]
- to_status: str
- comment: Optional[str]
- created_at: datetime

CreateTimesheetRequest:
- week_start_date: date

UpsertTimesheetEntryRequest:
- board_id: Optional[UUID] = None
- task_id: Optional[UUID] = None
- entry_date: date
- hours: float = Field(gt=0, le=24)
- entry_type: Literal['task','meeting','general','leave','holiday'] = 'task'
- description: Optional[str] = None

SubmitTimesheetRequest:
- member_note: Optional[str] = None

RecallTimesheetRequest:
- reason: str

### File 2: backend/app/routers/timesheets.py
FastAPI APIRouter with prefix="/timesheets" and tags=["Timesheets"]

GET /
Query params: status (optional filter), week_start_date (optional filter), user_id (optional, superadmin only)
Visibility rules (strictly enforced, not optional):
- If superadmin: full org visibility. Optionally filter by user_id. SELECT * FROM v_timesheets_canonical WHERE org_id=$1 [AND user_id=$2] [AND status=$3] ORDER BY week_start_date DESC LIMIT 52
- If manager: Return ONLY timesheets returned by fn_get_manager_accessible_timesheet_ids(user_id, org_id).

This stored function is the single source of truth for manager visibility.

Managers NEVER receive organization-wide visibility.
- If member: return own timesheets only. SELECT * FROM v_timesheets_canonical WHERE org_id=$1 AND user_id=$2 [AND status=$3] ORDER BY week_start_date DESC LIMIT 52
- Returns List[TimesheetResponse]

POST /
Body: CreateTimesheetRequest
- Call SELECT * FROM fn_create_timesheet($1,$2,$3) → user_id, org_id, week_start_date
- Returns TimesheetResponse 201.

GET /{timesheet_id}
- SELECT * FROM v_timesheets_canonical WHERE id=$1 AND org_id=$2
- Validate access:
- Members can only view their own timesheets.
- Managers can ONLY view a timesheet if fn_check_timesheet_approver_access(current_user.id, timesheet_id) returns TRUE.
- Superadmins have unrestricted organization-wide access.
- SELECT * FROM v_timesheet_entries_canonical WHERE timesheet_id=$1 ORDER BY entry_date, created_at
- SELECT * FROM v_timesheet_audit_canonical WHERE timesheet_id=$1 ORDER BY created_at
- Return TimesheetDetailResponse

POST /{timesheet_id}/entries
Body: UpsertTimesheetEntryRequest
- Validate ownership (only owner can add entries).
- Call SELECT * FROM fn_upsert_timesheet_entry($1,$2,$3,$4,$5,$6,$7,$8) → timesheet_id, user_id, board_id, task_id, entry_date, hours, entry_type, description
- Returns TimesheetEntryResponse 201.

DELETE /{timesheet_id}/entries/{entry_id}
- Validate ownership.
- Call SELECT fn_delete_timesheet_entry($1,$2) → entry_id, user_id
- Returns 204.

POST /{timesheet_id}/submit
Body: SubmitTimesheetRequest
- Validate ownership.
- Extract ip_address and user_agent from request.
- Call SELECT * FROM fn_submit_timesheet($1,$2,$3,$4,$5)
- Returns updated TimesheetResponse.

POST /{timesheet_id}/recall
Body: RecallTimesheetRequest
- Validate ownership.
- Extract ip_address and user_agent.
- Call SELECT * FROM fn_recall_timesheet($1,$2,$3,$4,$5)
- Returns updated TimesheetResponse.

Include proper HTTP exception handling for all stored function errors (catch asyncpg.exceptions.RaiseError and map to appropriate HTTP status codes).
Also show the two lines to add to main.py to register this router.
```

---

## Phase 4 — Backend: Approval Workflow APIs

**New file:** `backend/app/routers/timesheet_approvals.py`
**New file:** `backend/app/schemas/timesheet_approvals.py`

Endpoints:

- `GET /api/v1/timesheets/approvals/queue` — manager's pending approval queue
- `GET /api/v1/timesheets/approvals/queue/summary` — queue KPI counts (pending, approved this week, rejected)
- `POST /api/v1/timesheets/{id}/approve` — approve
- `POST /api/v1/timesheets/{id}/reject` — reject with mandatory comment

---

### PROMPT 4 — Backend: Approval Workflow APIs

```
You are a senior Python/FastAPI engineer working on KAIO.

## Architecture Rules (NON-NEGOTIABLE)
- No raw SQL. Views for reads, fn_* for writes.
- Pydantic v2. asyncpg. JWT dependency. Standard error format.

## Task
Create two files:

### File 1: backend/app/schemas/timesheet_approvals.py

ApprovalQueueItemResponse (extends TimesheetResponse from timesheets.py):
- days_since_submitted: int (computed from submitted_at)
- is_overdue: bool (submitted_at older than 48h)
- boards_involved: List[str] (distinct board names from entries)

ApprovalQueueSummaryResponse:
- pending_count: int
- approved_this_week: int
- rejected_this_week: int
- avg_hours_approved: float
- oldest_pending_days: Optional[int]

ApproveTimesheetRequest:
- comment: Optional[str] = None

RejectTimesheetRequest:
- comment: str (mandatory — reject always needs a reason)

### File 2: backend/app/routers/timesheet_approvals.py
FastAPI APIRouter with prefix="/timesheets" and tags=["Timesheet Approvals"]

All endpoints require manager or superadmin role. Return 403 if member tries to access.

GET /approvals/queue
Query params: status (default 'submitted'), board_id (optional filter)
- SELECT * FROM v_timesheets_canonical WHERE org_id=$1 AND approver_id=$2 AND status=$3 ORDER BY submitted_at ASC
- Enrich each row: compute days_since_submitted, is_overdue.
- For each timesheet, query boards_involved: SELECT DISTINCT board_name FROM v_timesheet_entries_canonical WHERE timesheet_id=$1
- Return List[ApprovalQueueItemResponse]

GET /approvals/queue/summary
- Run 4 separate queries against v_timesheets_canonical:
  1. COUNT where approver_id=$1 AND status='submitted'
  2. COUNT where approver_id=$1 AND status='approved' AND reviewed_at >= date_trunc('week', NOW())
  3. COUNT where approver_id=$1 AND status='rejected' AND reviewed_at >= date_trunc('week', NOW())
  4. AVG(total_hours) where approver_id=$1 AND status='approved' last 30 days
  5. MAX(NOW()-submitted_at) where approver_id=$1 AND status='submitted' → oldest pending
- Return ApprovalQueueSummaryResponse

POST /{timesheet_id}/approve
Body: ApproveTimesheetRequest
- Call SELECT fn_check_timesheet_approver_access($1,$2) → user_id, timesheet_id. 403 if false.
- Extract ip and user_agent.
- Call SELECT * FROM fn_approve_timesheet($1,$2,$3,$4,$5)
- Return updated TimesheetResponse.

POST /{timesheet_id}/reject
Body: RejectTimesheetRequest
- Validate comment is non-empty. 422 if empty.
- Call fn_check_timesheet_approver_access. 403 if false.
- Call SELECT * FROM fn_reject_timesheet($1,$2,$3,$4,$5)
- Return updated TimesheetResponse.

Note: fn_reject_timesheet reverts status to 'draft' so member can correct and resubmit. The response will reflect the new draft status.

Show the two main.py lines to register this router.
```

---

## Phase 5 — Frontend: Admin Configuration UI

**New files:**

- `frontend/src/features/timesheets/admin/TimesheetPolicyForm.tsx`
- `frontend/src/features/timesheets/admin/ApproverAssignmentManager.tsx`
- `frontend/src/features/timesheets/admin/TimesheetAdminPage.tsx`
- `frontend/src/services/timesheetAdminService.ts`

---

### PROMPT 5 — Frontend: Admin Configuration UI

```
You are a senior React/TypeScript engineer working on KAIO, an enterprise Kanban platform.

## Design System
- React 18 + TypeScript + Tailwind CSS
- Glassmorphism UI: dark bg, glass cards with backdrop-blur, purple/blue accent colors
- Icon library: Lucide React
- Existing components to reuse: Button, Modal, Input, Badge, Avatar from src/components/ui
- Existing RBAC utility: isManagerOrAdmin(user) and isSuperAdmin(user) from src/lib/rbac
- Axios instance from src/lib/axios for all HTTP calls
- Routing via React Router v6

## Task
Create 4 files:

### File 1: frontend/src/services/timesheetAdminService.ts
TypeScript service with typed interfaces and axios calls:

Interfaces:
- TimesheetPolicy (all fields from TimesheetPolicyResponse)
- ApproverAssignment (all fields from ApproverAssignmentResponse)
- EligibleApprover (user_id, display_name, email, role)

Functions:
- getTimesheetPolicy(): Promise<TimesheetPolicy>
- updateTimesheetPolicy(data: Partial<TimesheetPolicy>): Promise<TimesheetPolicy>
- getApproverAssignments(): Promise<ApproverAssignment[]>
- getEligibleApprovers(): Promise<EligibleApprover[]>
- assignApprover(data: {board_id: string|null, approver_user_id: string}): Promise<ApproverAssignment>
- removeApprover(assignmentId: string): Promise<void>

All functions use the configured axios instance. Proper TypeScript return types. No raw fetch calls.

### File 2: frontend/src/features/timesheets/admin/TimesheetPolicyForm.tsx
A settings form card component (not a modal) for superadmins to configure org-wide timesheet policy.

Fields to render:
1. Week Start Day — <select> dropdown with all 7 days
2. Standard Hours/Day — number input (0.5–24, step 0.5)
3. Standard Hours/Week — number input (1–168)
4. Max Hours/Day — number input (1–24)
5. Overtime Policy — radio group: "No Overtime Tracking" / "Flag as Overtime" / "Block Submission"
6. Submission Deadline — number input with label "Days after week end to submit" (0–30)
7. Allow Future Date Entries — toggle switch
8. Allow Past Entry (days back) — number input (0–365)
9. Require Task Link — toggle switch with helper text "Every time entry must be linked to a Kanban task"
10. Allow Member Recall — toggle switch with helper text "Members can recall a submitted timesheet before it is approved"

On submit: call updateTimesheetPolicy. Show success toast. Show field-level validation errors.
Show loading skeleton while fetching policy. Disable all fields and show "View Only" badge if user is manager or member (only superadmins can edit policy).

### File 3: frontend/src/features/timesheets/admin/ApproverAssignmentManager.tsx
Component for managing which manager approves which board's timesheets.

Features:
- Header: "Timesheet Approvers" with subtitle "Assign who reviews each project's timesheets. If no board-specific approver is set, the org-level approver handles it."
- Assignment list table with columns: Board / Approver / Assigned By / Actions (Remove button)
- Org-level fallback row always shown at top with label "All Projects (fallback)" and a special badge.
- Add Assignment form (inline, not modal):
  - Board selector dropdown (list of boards from existing board service, plus "All Projects (fallback)" option)
  - Approver selector dropdown (from getEligibleApprovers, shows name + role badge)
  - "Assign" button
- Remove button on each row triggers removeApprover with confirm dialog.
- Empty state: "No approvers assigned yet. Add one above."
- Add Assignment form and Remove buttons are disabled/hidden for managers and members. Only superadmins can mutate approver assignments; managers see the list read-only.

### File 4: frontend/src/features/timesheets/admin/TimesheetAdminPage.tsx
Full page layout combining both components above.

- Route guard: redirect to /dashboard if user is a member. Superadmins get full edit access; managers get read-only access to policy and approver list.
- Page header: "Timesheet Configuration" with Settings icon.
- Two-column layout on desktop (policy form left, approver manager right). Single column on mobile.
- Tab navigation: "Policy" | "Approvers" | "Reports" (Reports tab shows "Coming soon" placeholder).
- Use existing page layout/shell pattern from the codebase (check how other settings pages are structured).

Show the React Router route to add in the routes config:
<Route path="/settings/timesheets" element={<ProtectedRoute><TimesheetAdminPage /></ProtectedRoute>} />

And the nav link to add in the admin sidebar navigation (check existing sidebar component location).
```

---

## Phase 6 — Frontend: Member Timesheet Entry UI

**New files:**

- `frontend/src/features/timesheets/member/TimesheetWeekView.tsx`
- `frontend/src/features/timesheets/member/TimeEntryRow.tsx`
- `frontend/src/features/timesheets/member/TimesheetSummaryBar.tsx`
- `frontend/src/features/timesheets/member/MyTimesheetsPage.tsx`
- `frontend/src/services/timesheetService.ts`

---

### PROMPT 6 — Frontend: Member Timesheet Entry UI

```
You are a senior React/TypeScript engineer working on KAIO.

## Design System
- React 18 + TypeScript + Tailwind CSS + Glassmorphism dark theme
- Lucide React icons
- Reuse: Button, Modal, Input, Badge, Avatar from src/components/ui
- Axios from src/lib/axios

## Feature Context
This is a Tempo-style weekly timesheet view for members to log their hours against tasks/boards. Think of it like a spreadsheet-meets-kanban interaction: rows are work items, columns are days of the week, cells are hour inputs.

## Task
Create 5 files:

### File 1: frontend/src/services/timesheetService.ts
TypeScript service:

Interfaces:
- Timesheet, TimesheetEntry, TimesheetAudit, TimesheetDetail (mirror backend response schemas)
- CreateTimesheetRequest: { week_start_date: string }
- UpsertEntryRequest: { board_id?, task_id?, entry_date, hours, entry_type, description? }

Functions:
- getMyTimesheets(params?: {status?, week_start_date?}): Promise<Timesheet[]>
- createTimesheet(data: CreateTimesheetRequest): Promise<Timesheet>
- getTimesheetDetail(id: string): Promise<TimesheetDetail>
- upsertEntry(timesheetId: string, data: UpsertEntryRequest): Promise<TimesheetEntry>
- deleteEntry(timesheetId: string, entryId: string): Promise<void>
- submitTimesheet(id: string, data: {member_note?: string}): Promise<Timesheet>
- recallTimesheet(id: string, data: {reason: string}): Promise<Timesheet>

### File 2: frontend/src/features/timesheets/member/TimeEntryRow.tsx
A single row in the weekly grid representing one work item.

Props:
- boardName: string
- taskTitle?: string
- entries: TimesheetEntry[] (filtered for this board+task combination)
- weekDates: Date[] (7 dates for the week)
- policy: TimesheetPolicy
- readOnly: boolean
- onHoursChange: (date: Date, hours: number) => void
- onDescriptionChange: (date: Date, description: string) => void
- onDelete: (entryId: string) => void

Render:
- Left column: board badge (colored dot + name) and task name (smaller text below). If no task, show "General / [board name]"
- 7 day cells: each is a compact hour input (number, 0–24, step 0.5). Show red border if hours exceed policy.max_hours_per_day. Show orange tint if is_overtime flag is set. Empty cell shows placeholder "—".
- Right column: row total hours (sum of all 7 days for this row).
- On hover: show a description popover/tooltip input for that cell.
- Read-only mode: show hours as static text, no inputs.

### File 3: frontend/src/features/timesheets/member/TimesheetSummaryBar.tsx
Sticky bottom bar showing live totals while editing.

Props:
- timesheet: Timesheet
- policy: TimesheetPolicy
- onSubmit: () => void
- onRecall: () => void
- isSubmitting: boolean

Render:
- Left: "Week of [Mon DD] – [Sun DD]"
- Center: 7 day columns each showing that day's total hours. Color code: grey=0, blue=logged, orange=overtime, red=over max
- Right: "Total: XX.X / YY.Y hrs" — red if over, green if on target, grey if under
- Status badge: DRAFT / SUBMITTED / APPROVED / REJECTED chip
- Action button: "Submit Timesheet" (draft) / "Recall" (submitted) / disabled (approved)
- If status is REJECTED: show "Rejected: [comment]" banner above bar in red.

### File 4: frontend/src/features/timesheets/member/TimesheetWeekView.tsx
The main weekly timesheet grid component. This is the centrepiece of the feature.

Props:
- timesheetId: string (load detail on mount)
- onStatusChange: (newStatus: string) => void

State:
- timesheetDetail: TimesheetDetail | null
- policy: TimesheetPolicy | null
- pendingChanges: Map<string, UpsertEntryRequest> (debounced save)
- isSaving: boolean
- showSubmitModal: boolean
- showRecallModal: boolean

Features:
1. Header row: 7 day columns (Mon–Sun, with date). Highlight today. Mark past/future cells.
2. Group rows by board. Show board section header with total hours for that board.
3. "+ Add Entry" button per board section → opens inline entry picker (task selector dropdown from board's tasks, or "General" option, or entry type selector for leave/holiday).
4. Auto-save: debounce 800ms. Show "Saving..." indicator top-right when pending. "Saved" on success.
5. "Add Board" button at bottom → shows board picker modal from user's accessible boards.
6. Policy warnings shown as inline banners: "You have X entries missing task links" if require_task_link is on.
7. Submission deadline warning: "Deadline to submit: [date]" shown as amber banner if within 24h.

### File 5: frontend/src/features/timesheets/member/MyTimesheetsPage.tsx
The main timesheets page for members.

Layout:
- Header: "My Timesheets" with week navigation arrows (← Previous Week | Current Week | Next Week →)
- Current week auto-creates a timesheet on page load if none exists (call createTimesheet).
- Week selector shows status chip per week in the navigation (DRAFT / SUBMITTED / APPROVED / REJECTED).
- Main content: TimesheetWeekView for selected week.
- Side panel (collapsible on mobile): "Past Timesheets" list showing last 12 weeks with status, hours, quick link.
- Global status banner at top if any timesheet is REJECTED (red) with "View and Resubmit" CTA.

Add route: <Route path="/timesheets" element={<ProtectedRoute><MyTimesheetsPage /></ProtectedRoute>} />
Add nav link in sidebar between "My Work" and "Boards".
```

---

## Phase 7 — Frontend: Manager Approval UI

**New files:**

- `frontend/src/features/timesheets/approvals/ApprovalQueuePage.tsx`
- `frontend/src/features/timesheets/approvals/TimesheetReviewModal.tsx`
- `frontend/src/features/timesheets/approvals/ApprovalQueueSummaryCards.tsx`
- `frontend/src/services/timesheetApprovalService.ts`

---

### PROMPT 7 — Frontend: Manager Approval UI

```
You are a senior React/TypeScript engineer working on KAIO.

## Design System
- React 18 + TypeScript + Tailwind CSS + Glassmorphism dark theme
- Lucide React icons. Reuse existing UI primitives.

## Task
Create 4 files:

### File 1: frontend/src/services/timesheetApprovalService.ts
Interfaces + axios calls:
- getApprovalQueue(params?: {status?, board_id?}): Promise<ApprovalQueueItem[]>
- getApprovalQueueSummary(): Promise<ApprovalQueueSummary>
- approveTimesheet(id: string, data: {comment?: string}): Promise<Timesheet>
- rejectTimesheet(id: string, data: {comment: string}): Promise<Timesheet>
Types match backend approval response schemas.

### File 2: frontend/src/features/timesheets/approvals/ApprovalQueueSummaryCards.tsx
4 metric cards row at the top of the approvals page:
- "Pending Review" (count, amber clock icon)
- "Approved This Week" (count, green check icon)
- "Rejected This Week" (count, red X icon)
- "Avg Hours Approved" (float, blue chart icon)
If oldest_pending_days > 2: show "⚠ Oldest pending: X days" warning below the pending card.
Loading skeleton state. Error state with retry.

### File 3: frontend/src/features/timesheets/approvals/TimesheetReviewModal.tsx
Full-screen modal (or large side drawer) for reviewing a timesheet before approve/reject.

Props:
- timesheetId: string
- onClose: () => void
- onApproved: (ts: Timesheet) => void
- onRejected: (ts: Timesheet) => void

Sections:
1. Header: "[Name]'s Timesheet — Week of [date]" + status badge
2. Summary row: Total Hours / Standard Hours / Delta (+ or - formatted in red/green)
3. Weekly grid (read-only): Same TimeEntryRow grid but readOnly=true. Shows all entries grouped by board.
4. Audit log timeline: Vertical timeline showing status transitions with actor, timestamp, comment.
5. Member Note (if any): Quote block.
6. Action section at bottom:
   - "Approve" button (green) → opens inline confirm with optional comment input → calls approveTimesheet
   - "Reject" button (red) → opens inline reject form with REQUIRED comment textarea → calls rejectTimesheet
   - Both show loading state while API call in progress.
   - On success: show success toast, call onApproved/onRejected, close modal.

### File 4: frontend/src/features/timesheets/approvals/ApprovalQueuePage.tsx
Full manager approval queue page.

Layout:
- Header: "Timesheet Approvals" with Managers Only badge (RBAC gated — redirect members to /timesheets)
- ApprovalQueueSummaryCards at top
- Filter bar: Status filter tabs (All / Pending / Approved / Rejected) + Board filter dropdown
- Table/list of timesheets:
  Columns: Member Avatar+Name | Week | Status | Total Hours | Days Since Submitted | Boards Involved | Actions
  - "Review" button opens TimesheetReviewModal.
  - Row click also opens modal.
  - Overdue rows (>48h pending) shown with amber left border.
- Empty state per filter: "No timesheets pending review" with illustration.
- Real-time: poll every 60s for new items (or use existing WebSocket if available).
- Pagination: show 25 per page.

RBAC gate: if current user is a member, redirect to /timesheets (their own timesheet page). Only managers and superadmins can access the approval queue.
Add route: <Route path="/timesheets/approvals" element={<ProtectedRoute><ApprovalQueuePage /></ProtectedRoute>} />
Add nav link in sidebar (only visible to managers/superadmins) after "Timesheets".
```

---

## Phase 8 — Notifications, Audit Trail & Reports

**Extends:** Existing `NotificationService`, activity logging, dashboard

---

### PROMPT 8 — Notifications, Audit Trail & Reports

```
You are a senior full-stack engineer working on KAIO.

## Context
- Existing NotificationService at backend/app/services/notification_service.py
- Existing fn_create_notification stored proc
- Existing v_notifications_canonical with entity target deep-links
- Existing activity logging via activity table
- Existing dashboard at /api/v1/dashboard/summary using v_dashboard_kpis_canonical

## Task: 4 parts

### Part 1: Notification Integration (backend)
Modify or extend backend/app/services/notification_service.py to add:

notify_timesheet_submitted(timesheet_id, submitter_id, approver_id, week_label)
→ Creates notification for approver_id:
  title: "[Name] submitted a timesheet for [Week]"
  entity_type: "timesheet"
  entity_id: timesheet_id
  deep_link: "/timesheets/approvals?id={timesheet_id}"

notify_timesheet_approved(timesheet_id, submitter_id, approver_id, week_label)
→ Creates notification for submitter_id:
  title: "Your timesheet for [Week] was approved"
  entity_type: "timesheet", deep_link: "/timesheets?id={timesheet_id}"

notify_timesheet_rejected(timesheet_id, submitter_id, approver_id, week_label, comment)
→ Creates notification for submitter_id:
  title: "Your timesheet for [Week] needs revision"
  body: comment (first 120 chars)
  deep_link: "/timesheets?id={timesheet_id}"

notify_timesheet_recalled(timesheet_id, submitter_id, approver_id, week_label, reason)
→ Creates notification for approver_id:
  title: "[Name] recalled their timesheet for [Week]"
  deep_link: "/timesheets/approvals"

These functions should be called from within the stored procedures (fn_submit_timesheet, fn_approve_timesheet, fn_reject_timesheet, fn_recall_timesheet) via a Python hook, OR alternatively add them as calls in the API router after the fn_* call succeeds. Show the cleanest approach given the existing architecture.

### Part 2: Migration 044 — Timesheet Reports Views
File: database/migrations/044_timesheet_reports_views.sql

Create these views for reporting:

v_timesheet_org_summary_canonical:
Per org, per week:
- week_start_date
- total_members_who_submitted INT
- total_timesheets_submitted INT
- total_timesheets_approved INT
- total_timesheets_rejected INT
- total_timesheets_pending INT
- total_hours_logged NUMERIC
- avg_hours_per_member NUMERIC
- compliance_rate NUMERIC (submitted / total org members who should have submitted * 100)

v_timesheet_member_summary_canonical:
Per user, per org, last 12 weeks:
- user_id, display_name, email
- week_start_date
- status
- total_hours
- is_on_time BOOLEAN (submitted_at <= policy submission deadline)

v_timesheet_board_hours_canonical:
Per board, per week:
- board_id, board_name
- week_start_date
- total_hours_logged NUMERIC
- member_count INT (distinct users who logged to this board)

### Part 3: Reports API Endpoint
Add to backend/app/routers/timesheet_admin.py:

GET /timesheets/reports/org-summary
Requires manager or superadmin.
Query params: weeks_back (default 12, max 52)
SELECT * FROM v_timesheet_org_summary_canonical WHERE org_id=$1 ORDER BY week_start_date DESC LIMIT $2
Returns list of weekly org summary rows.

GET /timesheets/reports/board-hours

Superadmin
- organization-wide report

Manager
- report scoped ONLY to boards they are explicitly assigned as approver on
Query params: weeks_back (default 8), board_id (optional)
SELECT * FROM v_timesheet_board_hours_canonical WHERE org_id=$1 [...] ORDER BY week_start_date DESC
Returns board hours breakdown.

GET /timesheets/reports/member-compliance
Requires superadmin.
SELECT * FROM v_timesheet_member_summary_canonical WHERE org_id=$1 ORDER BY week_start_date DESC, display_name

### Part 4: Dashboard Integration (frontend)
Extend the existing dashboard summary cards (check frontend/src/features/ for the dashboard component) to add a new "Timesheets" section visible to managers/superadmins showing:
- Card: "Pending Approvals" (count with link to /timesheets/approvals)
Superadmin:
- Organization-wide KPIs.

Manager:
- KPIs computed ONLY from boards they are explicitly assigned as approver on.

Pull data from GET /timesheets/reports/org-summary?weeks_back=1 (latest week only for dashboard).
Integrate into the existing dashboard layout without breaking existing KPI cards.
```

---

## Phase 9 — Hardening, Edge Cases & Integration Tests

---

### PROMPT 9 — Hardening, Edge Cases & Integration Tests

```
You are a senior QA/Platform engineer working on KAIO.

## Context
The KAIO Timesheet feature spans:
- 8 PostgreSQL migrations (037–044) with stored functions and canonical views
- 3 FastAPI routers: timesheet_admin.py, timesheets.py, timesheet_approvals.py
- 4 React feature folders: admin/, member/, approvals/ + services

## Task: 4 hardening areas

### Area 1: Edge Cases — Stored Function Hardening
Review and add explicit error handling for these scenarios in the PL/pgSQL functions:

1. fn_submit_timesheet:
   - Timesheet has zero entries → RAISE EXCEPTION 'EMPTY_TIMESHEET'
   - Policy submission_deadline exceeded → RAISE EXCEPTION 'SUBMISSION_DEADLINE_PASSED' with deadline date in message
   - No approver found (no board assignment AND no org fallback) → RAISE EXCEPTION 'NO_APPROVER_CONFIGURED' — do NOT block submission, instead set approver_id=NULL and flag for superadmin notification
   - Timesheet already submitted → RAISE EXCEPTION 'ALREADY_SUBMITTED'

2. fn_upsert_timesheet_entry:
   - Entry date outside week_start_date to week_end_date → RAISE EXCEPTION 'DATE_OUT_OF_WEEK_RANGE'
   - Entry date is future AND policy.allow_future_entry=false → RAISE EXCEPTION 'FUTURE_ENTRY_NOT_ALLOWED'
   - Entry date older than NOW() - policy.allow_past_entry_days → RAISE EXCEPTION 'PAST_ENTRY_NOT_ALLOWED'
   - Hours would push day total over policy.max_hours_per_day AND policy.overtime_policy='block_submission' → RAISE EXCEPTION 'OVERTIME_BLOCKED'

3. fn_assign_timesheet_approver:
   - Assigned approver has role 'member' (only managers and superadmins may be approvers) → RAISE EXCEPTION 'INVALID_APPROVER_ROLE'
   - Same board already has active assignment for same approver → silently return existing (idempotent)
   - Assigning to a board that belongs to a different org → RAISE EXCEPTION 'BOARD_ORG_MISMATCH'

Show the updated PL/pgSQL bodies (delta only — just the added RAISE EXCEPTION blocks and guards).

### Area 2: FastAPI Error Mapping
Create backend/app/routers/timesheet_errors.py:

A mapping dict TIMESHEET_ERROR_MAP: Dict[str, tuple[int, str]] that maps stored proc error codes to (HTTP_status_code, user_friendly_message):
- 'EMPTY_TIMESHEET' → (422, "Cannot submit an empty timesheet. Please add at least one time entry.")
- 'SUBMISSION_DEADLINE_PASSED' → (422, "The submission deadline for this timesheet has passed.")
- 'NO_APPROVER_CONFIGURED' → (202, "Timesheet submitted. Note: no approver is configured — a superadmin will be notified.")
- 'ALREADY_SUBMITTED' → (409, "This timesheet has already been submitted.")
- 'DATE_OUT_OF_WEEK_RANGE' → (422, "Entry date must fall within the timesheet's week.")
- 'FUTURE_ENTRY_NOT_ALLOWED' → (422, "Future date entries are not allowed by your organization's policy.")
- 'PAST_ENTRY_NOT_ALLOWED' → (422, "This date is beyond the allowed lookback window.")
- 'OVERTIME_BLOCKED' → (422, "This entry would exceed the maximum hours per day. Overtime entries are blocked by policy.")
- 'INVALID_APPROVER_ROLE' → (422, "The selected approver must be a Manager or Superadmin. Members cannot be assigned as approvers.")
- 'BOARD_ORG_MISMATCH' → (403, "The selected board does not belong to your organization.")

Add a reusable handle_timesheet_db_error(exc: asyncpg.exceptions.RaiseError) function that looks up the error code in the map and raises HTTPException with the mapped status and message.
Import and use this handler in all three timesheet routers' try/except blocks.

### Area 3: Pytest Integration Tests
Create backend/tests/test_timesheets.py:

Write pytest tests using pytest-asyncio and the existing test fixtures (check backend/tests/ for conftest.py patterns):

test_policy_upsert_superadmin_only: assert 403 when member tries PUT /timesheets/policy
test_policy_default_returned: assert GET /timesheets/policy returns sensible defaults even before any policy is set
test_create_timesheet_duplicate_week: assert 409 when creating two timesheets for same week
test_entry_outside_week_rejected: assert 422 when adding entry with date outside week range
test_overtime_blocked_by_policy: configure policy overtime_policy='block_submission', assert 422 when hours exceed max
test_submit_empty_timesheet: assert 422 when submitting timesheet with no entries
test_submit_and_approve_flow: full happy path — create → add entries → submit → approve → verify status=approved
test_submit_and_reject_flow: create → submit → reject → verify status=draft (revert) → resubmit → approve
test_recall_flow: submit → recall → verify status=draft
test_recall_not_allowed_when_policy_disabled: set allow_member_recall=false → submit → recall → assert 403
test_member_cannot_see_others_timesheet: assert 403 when member A tries GET /timesheets/{member_B_timesheet_id}
test_manager_can_only_see_assigned_board_timesheets

Scenario:

Board A -> Manager A

Board B -> Manager B

Verify:

Manager A can view Board A timesheets.

Manager A cannot view Board B timesheets.

Manager B can view Board B timesheets.

Superadmin can view both.
test_member_cannot_access_approval_queue: assert 403 when member tries GET /timesheets/approvals/queue
test_member_cannot_approve: assert 403 when member tries POST /timesheets/{id}/approve
test_approval_requires_assigned_approver: assert 403 when a manager who is NOT the assigned approver tries to approve
test_notification_sent_on_submit: mock NotificationService, assert notify_timesheet_submitted was called
test_deadline_enforcement: set submission_deadline_days=0 (deadline = week end day), attempt submit after deadline → assert 422
test_audit_log_populated: after full submit→approve flow, assert audit log has 2 entries with correct from/to statuses

### Area 4: Frontend Error Handling
Create frontend/src/features/timesheets/shared/TimesheetErrorBanner.tsx:

Props: error: {error_code: string, detail: string} | null

Renders a contextual banner using the error_code to provide human-friendly messaging and actionable CTAs:
- SUBMISSION_DEADLINE_PASSED → amber banner "Your submission window has closed. Contact your manager."
- OVERTIME_BLOCKED → red banner "Overtime is blocked by policy. Reduce hours to [max] per day."
- NO_APPROVER_CONFIGURED → blue info banner "Submitted. Your organization hasn't assigned an approver yet — a superadmin has been notified."
- EMPTY_TIMESHEET → yellow warning "Add at least one time entry before submitting."
- Generic fallback: show detail field directly.

Use this component in TimesheetWeekView.tsx and TimesheetReviewModal.tsx for all API error states.
```

---

## Phase 9.5 — End-to-End Real-Life Debug, Stress & Edge Case Test Phase

---

### PROMPT 9.5 — End-to-End Real-Life Testing, Edge Cases, Race Conditions & Production-Grade Stress Test

```
You are a Lead QA Architect & Senior Full-Stack Debugging Engineer working on KAIO.

## Context & Objectives
Phases 1 through 9 introduce the database schema, FastAPI endpoints, RBAC policies, React UI components, notifications, and error handling for the KAIO Timesheet feature. Before proceeding to Phase 10 (Tempo-Style Calendar View), we must perform an end-to-end audit, resolve runtime 404/connectivity issues, eliminate placeholder/dummy UI states, test complex race conditions, and conduct production-grade stress testing.

## Step 1: Backend Router Registration & Server Restart
1. Verify why `/api/v1/timesheets` returns 404:
   - Ensure `backend/app/routers/timesheets.py`, `timesheet_admin.py`, and `timesheet_approvals.py` are imported and registered with `app.include_router(..., prefix="/api/v1")` in `backend/app/main.py`.
   - Ensure the server process running `uvicorn app.main:app` is restarted or running with `--reload` to reflect newly mounted router endpoints.
2. Database Schema Audit:
   - Run and verify all PostgreSQL migrations from `036_timesheet_enums.sql` through `043_timesheet_reports_views.sql`.
   - Validate that stored functions (`fn_upsert_timesheet_policy`, `fn_assign_timesheet_approver`, `fn_create_timesheet`, `fn_upsert_timesheet_entry`, `fn_submit_timesheet`, `fn_approve_timesheet`, `fn_reject_timesheet`, `fn_recall_timesheet`) exist and match signatures.

## Step 2: Frontend UI Wireup & Route Audit
1. Audit layout routing and navigation links:
   - Verify `/timesheets` (My Timesheets), `/timesheets/approvals` (Manager Approval Queue), and `/timesheets/admin` (Admin Policy Config) are connected in App routing (`App.tsx` or router configuration) and sidebar menu.
   - Verify RBAC gating (`isManagerOrAdmin`) correctly shows/hides tabs and routes.
2. Eliminate Dummy/Placeholder UI:
   - Audit `MyTimesheetsPage.tsx`, `TimesheetWeekView.tsx`, `ApprovalQueuePage.tsx`, `TimesheetReviewModal.tsx`, and `TimesheetAdminPage.tsx`.
   - Ensure all buttons (Save, Submit, Recall, Approve, Reject, Policy Save, Approver Assign) execute live API calls via `timesheetService`, `timesheetApprovalService`, and `timesheetAdminService`.
   - Replace any remaining `console.log` placeholders or mock fallbacks with real API hooks and handle loading states & `TimesheetErrorBanner` display.

## Step 3: Real-Life Human E2E Test Scenarios
Execute full multi-role user flows end-to-end:
1. Superadmin Flow:
   - Access Admin Configuration (`/timesheets/admin`).
   - Configure Policy: Week Start (Monday), Standard Hours (8h/day, 40h/week), Max Hours (12h/day), Overtime Policy (`block_submission`), Submission Deadline (Sunday 23:59), Past Entry Limit (14 days), Future Entry Allowed (false), Member Recall Allowed (true).
   - Assign Approvers: Assign Manager M1 to Board A, Manager M2 to Board B.
2. Member Flow (User U1 & User U2):
   - Access My Timesheets (`/timesheets`).
   - Create/Load weekly grid. Verify standard week header dates.
   - Log task hours across days for tasks in Board A and Board B. Verify row and column totals auto-calculate dynamically.
   - Test Draft Auto-save: edit hours, navigate away, re-open, verify persisted values.
   - Click Submit: status transitions from `DRAFT` → `SUBMITTED`. Verify UI grid becomes read-only with a "Submitted" status badge.
3. Manager Flow (Manager M1 & Manager M2):
   - Log in as Manager M1. Access Approval Queue (`/timesheets/approvals`).
   - Verify Board RBAC Isolation: Manager M1 can ONLY see timesheets containing entries for Board A (cannot see Board B entries).
   - Open `TimesheetReviewModal` for User U1. Review task breakdown, audit history log, and member note.
   - Reject Timesheet with comment: status changes `SUBMITTED` → `REJECTED` (reverts to `DRAFT` state for U1).
   - User U1 receives notification, updates hours, and re-submits.
   - Manager M1 opens modal and Approves timesheet: status changes `SUBMITTED` → `APPROVED`.

## Step 4: Edge Case Validation
1. Empty Timesheet Submission:
   - Create new week timesheet with 0 logged entries/hours and attempt submit → assert 422 `EMPTY_TIMESHEET` error banner displayed.
2. Boundary & Overtime Violations:
   - Attempt logging hours > max_hours_per_day (e.g. 14 hours) when overtime policy is `block_submission` → assert 422 `OVERTIME_BLOCKED` error banner.
   - Attempt logging hours on a future date when `allow_future_entry=false` → assert 422 `FUTURE_ENTRY_NOT_ALLOWED`.
   - Attempt logging hours older than 14 days when `allow_past_entry_days=14` → assert 422 `PAST_ENTRY_NOT_ALLOWED`.
3. Recall Workflow & Policy Lockout:
   - User U1 submits timesheet, then clicks "Recall" before approval → status reverts to `DRAFT`.
   - Change policy `allow_member_recall=false`. User U1 submits timesheet → verify "Recall" button is disabled/hidden in UI.

## Step 5: Race Condition & Concurrency Hardening
1. Double Submit Attack:
   - Simulate rapid multi-click on "Submit" button (or trigger simultaneous HTTP POST `/api/v1/timesheets/{id}/submit` requests) → verify only the first request succeeds (status `SUBMITTED`), subsequent requests return 409 `ALREADY_SUBMITTED` without breaking status or generating duplicate notifications.
2. Concurrent Edit & Approval:
   - Member attempts `PUT /entries` while Manager is executing `POST /approve` on the same timesheet.
   - Verify PostgreSQL transaction isolation (`FOR UPDATE` row lock in PL/pgSQL function `fn_approve_timesheet` / `fn_upsert_timesheet_entry`) rejects modifications once timesheet status is non-DRAFT.
3. Dual Manager Approval Race:
   - Two managers simultaneously attempt to approve/reject the same timesheet -> verify only one transaction commits, second returns state mismatch error cleanly.

## Step 6: Production-Grade Stress & Load Test
1. Automated Batch Submission:
   - Script 50 concurrent virtual users submitting timesheets simultaneously.
   - Monitor PostgreSQL connection pool, check query execution times on `v_timesheets_canonical` and `v_timesheet_entries_canonical`.
2. Frontend Rapid Input Stress:
   - Fast typing in weekly grid cells (stress debounced auto-save) → verify state consistency, no out-of-order API response overwrites, and no memory leaks.
```

---

## Phase 10 — Tempo-Style Calendar View & Daily Worklog Experience

**New files:**

- `frontend/src/features/timesheets/member/TimesheetCalendarView.tsx`
- `frontend/src/features/timesheets/member/LogTimeModal.tsx`
- `frontend/src/features/timesheets/member/DayDetailDrawer.tsx`
- `frontend/src/features/timesheets/shared/ViewModeSwitcher.tsx`
  **Extends:**
- `backend/app/routers/timesheets.py` (add `GET /api/v1/timesheets/calendar`)
- `frontend/src/services/timesheetService.ts`
- `frontend/src/features/timesheets/member/MyTimesheetsPage.tsx`

---

### PROMPT 10 — Tempo-Style Calendar View & Daily Worklog Experience

```
You are a senior React/TypeScript and FastAPI engineer working on KAIO.

## Context
The application currently supports a weekly spreadsheet grid view (`TimesheetWeekView.tsx`). To provide a Jira/Tempo-grade experience, members need a visual Calendar View (Month / Multi-Week) to visualize workload distribution, monitor daily capacity targets, and rapidly log time via date-cell interactions.

## Architecture & Design Guidelines
- Design System: React 18, Tailwind CSS with glassmorphism theme (`bg-slate-900/80`, `backdrop-blur-md`, `border-slate-800`), Lucide React icons (`Calendar`, `Clock`, `Plus`, `Grid`, `Filter`, `CheckCircle2`, `AlertCircle`, `Briefcase`).
- Daily Capacity Indicators: Standard day = 8.0h (from policy). Color code day cells:
  - Green border/ring: 100% capacity met (e.g. 8.0h)
  - Amber border/ring: Under capacity (1.0h - 7.5h)
  - Red ring/badge: Overtime (> policy.max_hours_per_day)
  - Muted slate: 0h logged
- Worklog Type Badges:
  - Task entries: Indigo/Blue chip
  - Meeting entries: Purple chip
  - General entries: Cyan chip
  - Leave / Holiday entries: Emerald chip

## Task: Implement 5 components & 1 backend API update

### Part 1: Backend Endpoint (`GET /api/v1/timesheets/calendar`)
Add to `backend/app/routers/timesheets.py`:

GET /api/v1/timesheets/calendar
Query params: start_date (date, required), end_date (date, required), user_id (optional, default current_user)
- Visibility rules: Members can only request their own user_id. Managers/Superadmins can query user_id if permitted by RBAC.
- Query v_timesheet_entries_canonical joined with v_timesheets_canonical for date range entry_date >= start_date AND entry_date <= end_date.
- Group entries by date and return daily summaries with capacity percentage, overtime flags, and entry list.

### Part 2: `frontend/src/features/timesheets/shared/ViewModeSwitcher.tsx`
Segmented control component for toggling between views:
- Options: `Grid View` (Table icon) | `Calendar View` (Calendar icon)
- Persists selected view preference in localStorage under `kaio_timesheet_view_mode`.

### Part 3: `frontend/src/features/timesheets/member/LogTimeModal.tsx`
Quick-entry modal for logging time directly on any date:
- Props: `isOpen: boolean`, `initialDate?: Date`, `onClose: () => void`, `onSuccess: () => void`
- Form fields: Date Picker (defaults to clicked date), Board Selector dropdown, Task Selector (filtered by board), Entry Type radio chips (Task, Meeting, General, Leave, Holiday), Hours Numeric Input (with quick +1h, +2h, +4h, +8h buttons), Work Description textarea.
- On Submit: calls `timesheetService.upsertEntry()`. If no timesheet exists for that week, auto-creates it via `createTimesheet()`.

### Part 4: `frontend/src/features/timesheets/member/DayDetailDrawer.tsx`
Slide-over drawer showing detailed worklogs for a selected day:
- Triggered by clicking a day header or "View Day Detail".
- Displays day header, total hours, capacity progress bar, list of logged entries with inline edit/delete, and "+ Log More Time" button.

### Part 5: `frontend/src/features/timesheets/member/TimesheetCalendarView.tsx`
The core Tempo Calendar component:
- View Mode selector: Month (30-31 days grid) | 2-Week | 1-Week.
- Navigation header: `← Previous Month` | `Today` | `Next Month →` with month title.
- Calendar Grid:
  - 7 column headers (Mon - Sun).
  - Day Cells: Day number, capacity progress ring/bar, up to 3 worklog chips shown per day (`+ N more` pill if truncated), quick "+ Log Time" button on hover.
  - Cell click → opens `LogTimeModal` pre-filled with date.
  - Click day header or "+ N more" → opens `DayDetailDrawer`.
- Bottom Legend: Capacity colors (Green: 100%, Amber: Partial, Red: Overtime) & Entry types.

### Part 6: Integration in `MyTimesheetsPage.tsx`
- Add `ViewModeSwitcher` to page header.
- Conditionally render `TimesheetWeekView` (Grid) or `TimesheetCalendarView` based on active mode.
- Top bar action button "+ Log Time" opens `LogTimeModal`.
```

---

## Data Flow Diagram (Full Feature)

```
[Superadmin]
    │
    ├── Configure Policy (week start, hours, overtime rules, deadlines)
    └── Assign Approvers (Board X → Manager Y, fallback org-level)
                            │
                            ▼
[Member]
    ├── Open My Timesheets → auto-create DRAFT for current week
    ├── Log hours per task/board per day (auto-save debounced)
    ├── Policy warnings enforced in real-time (overtime, task link, future dates)
    └── Submit → SUBMITTED (system resolves approver from assignment table)
                            │
                   Notification → Approver
                            │
                            ▼
[Assigned Board Approver]
    ├── Approval Queue (assigned boards only) → see pending timesheets
    ├── Review modal → see full grid, audit trail, member note
    ├── Approve → APPROVED → Notification → Member
    └── Reject (mandatory comment) → DRAFT → Notification → Member
                            │
                   [Member can edit and resubmit]
                            │
                   [Member can Recall if policy allows]
```

---

## RBAC Matrix

| Action                                  | Superadmin | Manager (Assigned Approver) | Manager (Not Assigned) | Member         |
| --------------------------------------- | ---------- | --------------------------- | ---------------------- | -------------- |
| Configure Policy                        | ✅         | ❌                          | ❌                     | ❌             |
| Assign Approvers                        | ✅         | ❌                          | ❌                     | ❌             |
| View Own Timesheets                     | ✅         | ✅                          | ✅                     | ✅             |
| Create/Edit Own Timesheet               | ✅         | ✅                          | ✅                     | ✅             |
| Submit Own Timesheet                    | ✅         | ✅                          | ✅                     | ✅             |
| Recall Own Timesheet                    | ✅         | ✅                          | ✅                     | ✅ (if policy) |
| View All Org Timesheets                 | ✅         | ❌                          | ❌                     | ❌             |
| View Timesheets (assigned boards only)  | ✅         | ✅                          | ❌                     | ❌             |
| Approve / Reject (assigned boards only) | ✅         | ✅                          | ❌                     | ❌             |
| View Reports (assigned boards only)     | ✅         | ✅                          | ❌                     | ❌             |
| View Org-Wide Reports & Compliance      | ✅         | ❌                          | ❌                     | ❌             |

---

## Migration Sequence Summary

| Migration | File                              | Contents                                 |
| --------- | --------------------------------- | ---------------------------------------- |
| 036       | `036_timesheet_enums.sql`         | New ENUM types                           |
| 037       | `037_timesheet_policy_schema.sql` | Policy + approver assignment tables      |
| 038       | `038_timesheet_core_schema.sql`   | timesheets + entries + audit_log tables  |
| 039       | `039_timesheet_indexes.sql`       | Performance indexes                      |
| 040       | `040_timesheet_functions.sql`     | All fn\_\* stored procedures             |
| 041       | `041_timesheet_triggers.sql`      | updated_at + total_hours recalc triggers |
| 042       | `042_timesheet_views.sql`         | All v\_\*\_canonical views               |
| 043       | `043_timesheet_reports_views.sql` | Reporting aggregate views                |

---

_Generated for KAIO Phase 4.0 — Knowledge Graph & Insights Sprint_
_Architecture: PostgreSQL 15+ / FastAPI / React 18 / Tailwind CSS_
