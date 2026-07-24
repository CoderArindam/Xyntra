# 02 — Backend Architecture

## 1. Executive Summary & Technology Stack

The KAIO backend is built using modern asynchronous Python architecture centered around **FastAPI** and **asyncpg**.

```
┌─────────────────────────────────────────────────────────────────┐
│                       FastAPI Application                       │
├─────────────────────────────────────────────────────────────────┤
│  Routers (API Layer) ──► Services Layer ──► DB Stored Procs     │
├─────────────────────────────────────────────────────────────────┤
│                     asyncpg Connection Pool                     │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                   ┌───────────────────────────┐
                   │ PostgreSQL 15+ Database   │
                   └───────────────────────────┘
```

### Core Technologies:
- **Framework**: FastAPI (v0.110+)
- **ASGI Server**: Uvicorn (v0.28+)
- **Database Driver**: `asyncpg` (v0.29+)
- **Auth**: PyJWT (pyjwt[crypto]) + bcrypt + Passlib — delivered via **httpOnly cookies**
- **Data Validation**: Pydantic v2 + Pydantic Settings
- **Browser Automation**: Playwright Python (v1.40+)
- **Audio Processing**: FFmpeg binary integration
- **Speech Engine**: Deepgram SDK (v3.0+)
- **HTTP Client**: httpx (v0.27+) — used by LLM providers
- **Email**: SMTP via Python `smtplib` (configured via `SMTP_EMAIL` / `SMTP_PASSWORD` env vars)

---

## 2. Architectural Rules & Constraints

> [!CAUTION]
> ### Mandatory Architectural Rule: NO Inline Raw SQL
> Under **NO circumstance** may Python routers or service classes execute raw SQL statements (`SELECT`, `INSERT`, `UPDATE`, `DELETE`).
> - **Read Operations**: Must select directly from canonical views (`v_*_canonical`).
> - **Write Operations**: Must call PostgreSQL user-defined functions or stored procedures (e.g., `SELECT fn_create_task(...)`).
> - **Violation Prevention**: Code reviews must fail if inline SQL query strings are found in application code.

---

## 3. Module Hierarchy & Directory Structure

```
backend/
├── .env                            # Environment configuration (DATABASE_URL, JWT_SECRET, etc.)
├── requirements.txt                # Python dependencies
├── app/
│   ├── main.py                     # Entry point, FastAPI app, CORS, static mounts, lifespan hooks
│   ├── ai/                         # LLM integration (Puter, Gemini, KAI agent, clarification router, orchestrator)
│   ├── auth/                       # JWT verification, password hashing, session tracking, RBAC
│   │   ├── dependencies.py         # get_current_user, require_proposal_review_access, require_meeting_initiation_access
│   │   ├── jwt.py                  # create_access_token, verify_token
│   │   ├── password.py             # bcrypt hash & verify helpers
│   │   └── permissions.py          # require_super_admin, require_manager_or_above
│   ├── config/
│   │   └── settings.py             # pydantic-settings: DATABASE_URL, JWT_SECRET, JWT_ALGORITHM, SMTP_*, FRONTEND_ORIGINS
│   ├── constants/                  # System constants & enums
│   ├── database/
│   │   └── connection.py           # asyncpg pool manager, get_db_connection dependency
│   ├── meeting/                    # Meeting pipeline subsystem (bot, recorder, orchestrator, attribution)
│   ├── routers/                    # 21 REST API route handlers:
│   │   ├── activity.py             # GET /activity — audit log history
│   │   ├── admin.py                # /admin — user/board CRUD (Superadmin-gated)
│   │   ├── ai.py                   # /ai — KAI AI agent endpoints
│   │   ├── attachments.py          # /tasks/{id}/attachments — file uploads & downloads
│   │   ├── auth.py                 # /auth — login, register org, me, refresh, logout, sessions, security events
│   │   ├── board_members.py        # /boards/{id}/members — membership queries
│   │   ├── boards.py               # /boards — CRUD, archiving
│   │   ├── comments.py             # /tasks/{id}/comments — create, list, delete
│   │   ├── dashboard.py            # /dashboard/summary — Manager/Superadmin KPI dashboard
│   │   ├── invitations.py          # /invitations — invite, list, verify, accept, revoke
│   │   ├── my_work.py              # /my-work — user task aggregation & summary
│   │   ├── notifications.py        # /notifications — list, mark read, mark all read
│   │   ├── organization.py         # /organization — org profile & settings
│   │   ├── preferences.py          # /preferences — user UI & notification preferences
│   │   ├── task_proposals.py       # /proposals — AI proposal review, approve, reject
│   │   ├── tasks.py                # /tasks — CRUD, move, reorder
│   │   ├── timesheets.py           # /timesheets — draft grid, entry upsert/delete, submit, recall
│   │   ├── timesheet_approvals.py  # /timesheets/approvals — manager approval queue, approve, reject
│   │   ├── timesheet_admin.py      # /timesheets/policy, /timesheets/approvers — policy & approver config, reports
│   │   ├── timesheet_errors.py     # Centralized stored procedure error code mapper
│   │   ├── users.py                # /users — user directory & profile queries
│   │   └── (meeting router)        # /meeting — mounted from app/meeting/api/router.py
│   ├── schemas/                    # Pydantic request/response DTO schemas (one file per domain, including timesheets)
│   └── services/                   # Business logic services:
│       ├── activity_service.py
│       ├── admin_service.py
│       ├── attachment_service.py
│       ├── auth_service.py
│       ├── board_service.py
│       ├── comment_service.py
│       ├── dashboard_service.py    # Reads v_dashboard_kpis_canonical, v_dashboard_board_summaries_canonical
│       ├── email_service.py        # SMTP email dispatch wrapper
│       ├── email_templates.py      # HTML email template generators
│       ├── invitation_service.py   # Full invitation lifecycle (invite → verify → accept → revoke)
│       ├── my_work_service.py
│       ├── notification_service.py # Includes timesheet lifecycle notification dispatches
│       ├── organization_service.py
│       ├── preferences_service.py
│       ├── project_settings.py     # Board project settings (icon, color, key, etc.)
│       ├── storage_service.py      # Local disk file storage
│       ├── task_service.py
│       └── user_service.py
└── tests/                          # Pytest automated test suites
```

---

## 4. Key Subsystem Breakdown

### 4.1 FastAPI Application Lifespan (`app/main.py`)
Manages startup and shutdown hooks using `asynccontextmanager`:
- **Startup**: Initializes `asyncpg` connection pool via `db.connect()`. Mounts `uploads/` directory as static files at `/uploads`.
- **Shutdown**: Safely cancels active meeting runtimes via `meeting_service.shutdown_all()`, then closes DB connections via `db.disconnect()`.

### 4.2 Database Connection Manager (`app/database/connection.py`)
- Maintains a global `Database` instance holding an `asyncpg.Pool`.
- Configures custom type codecs for JSON and JSONB fields using standard Python `json.dumps`/`json.loads`.
- Provides dependency `get_db_connection()` yielding non-blocking connections from pool.

### 4.3 Auth & Security Subsystem (`app/auth/`, `app/routers/auth.py`)

> [!IMPORTANT]
> **Auth uses httpOnly cookies, NOT Authorization headers.**
> - `POST /auth/login` → sets `access_token` cookie (15 min, httpOnly) + `refresh_token` cookie (7 days, httpOnly, path=`/api/v1/auth`)
> - `GET /auth/me` + all protected endpoints → reads `access_token` cookie (or fallback to `Authorization: Bearer` header)
> - `POST /auth/refresh` → reads `refresh_token` cookie, issues new cookies
> - `POST /auth/logout` → clears both cookies, optionally revokes session
> - `DELETE /auth/sessions/other` → revokes all non-current sessions

**RBAC Layers:**
- `get_current_user` — verifies JWT from cookie, checks `fn_is_session_revoked()` in DB
- `require_proposal_review_access` — calls `fn_check_proposal_review_access(user_id, org_id)` (Superadmin/Manager)
- `require_meeting_initiation_access` — calls `fn_check_meeting_initiation_access(user_id, org_id)` (Superadmin/Manager)
- `require_manager_or_above` — role string check (`MANAGER` or `SUPER_ADMIN`)
- `require_super_admin` — role string check (`SUPER_ADMIN` only)

**Session & Security features:**
- Multi-device JWT session tracking in `active_sessions` table (`fn_refresh_session`, `fn_is_session_revoked`)
- Security event logging (`fn_log_security_event`) tracking logins, password updates, session revocations, and role changes with IP and User-Agent metadata
- Configurable organization password policy endpoint (`GET /auth/password-policy`)

### 4.4 Meeting Subsystem (`app/meeting/`)
The meeting subsystem is self-contained and modular:
- `api/router.py`: Exposes endpoints for managing meeting sessions.
- `bot/recorder/recorder.py`: `MeetingRecorder` manages Playwright page injection and WebM stream assembly.
- `pipeline/orchestrator.py`: `MeetingPipelineOrchestrator` controls sequential execution of meeting stages.
- `services/meeting_service.py`: `MeetingService` maintains active runtime instances (`MeetingRuntime`) and background tasks.

### 4.5 Dashboard Service (`app/services/dashboard_service.py`)
Reads three canonical views in a single request cycle:
1. `v_dashboard_kpis_canonical` — org-wide KPIs (total tasks by status, overdue, boards, team size, pending proposals, active meetings)
2. `v_dashboard_board_summaries_canonical` — per-board task count, completion %, overdue count, member count
3. `v_activities_canonical` — last 10 recent activity entries

---

## 5. End-to-End Request Execution Flow

```mermaid
sequenceDiagram
    autonumber
    participant Client as React SPA / Client
    participant Router as FastAPI Router (app/routers)
    participant Auth as Auth Dependency (app/auth)
    participant Pool as asyncpg Connection Pool
    participant DB as PostgreSQL Database

    Client->>Router: POST /api/v1/tasks (JSON body, access_token cookie)
    Router->>Auth: get_current_user() — read cookie, verify JWT
    Auth->>DB: SELECT fn_is_session_revoked(session_id)
    DB-->>Auth: False (active session)
    Auth-->>Router: Current User Claims (user_id, org_id, role)
    Router->>Pool: Acquire Connection
    Pool-->>Router: Connection Handle
    Router->>DB: SELECT * FROM fn_create_task($1, $2, ...)
    DB-->>Router: Recordset (Created Task)
    Pool-->>Router: Release Connection
    Router-->>Client: 201 Created (Task JSON)
```

---

## 6. Major Classes & Interfaces Catalog

| Class / Interface | Path | Category | Responsibility |
|---|---|---|---|
| `FastAPI` | `app/main.py` | Framework | Top-level ASGI web application controller |
| `Database` | `app/database/connection.py` | Infrastructure | `asyncpg` pool lifecycle manager |
| `Settings` | `app/config/settings.py` | Config | pydantic-settings env config (`DATABASE_URL`, `JWT_SECRET`, `JWT_ALGORITHM`, `SMTP_*`, `FRONTEND_ORIGINS`) |
| `MeetingService` | `app/meeting/services/meeting_service.py` | Service | Global registry and manager of active meeting runtimes |
| `MeetingRuntime` | `app/meeting/services/meeting_service.py` | Domain | Container for session state, Playwright browser, event bus |
| `MeetingRecorder` | `app/meeting/bot/recorder/recorder.py` | Bot Engine | MediaRecorder script injection & WebM recording assembly |
| `MeetingPipelineOrchestrator` | `app/meeting/pipeline/orchestrator.py` | Orchestration | Sequential stage execution engine for post-processing |
| `PipelineContext` | `app/meeting/pipeline/context.py` | Domain Context | State context passed between pipeline stages containing artifacts |
| `DeepgramSpeechProvider` | `app/meeting/providers/speech/deepgram_provider.py` | Provider | Deepgram Nova-3 API client for STT and atomic diarization |
| `DynamicAttributionEngine` | `app/meeting/attribution/dynamic_engine.py` | Analytics Engine | Scores and aligns participant presence with speech turns |
| `NotificationService` | `app/services/notification_service.py` | Service | Generates system notifications for user assignments, comments, & proposals |
| `DashboardService` | `app/services/dashboard_service.py` | Service | Aggregates org KPIs, board summaries, and recent activity for Manager dashboard |
| `InvitationService` | `app/services/invitation_service.py` | Service | Full invitation lifecycle: invite → email → verify token → accept → revoke |
| `TaskProposalsRouter` | `app/routers/task_proposals.py` | API Router | Manages AI proposal queues, edits, approvals (`fn_approve_task_proposal`), and rejections |
| `AuthService` | `app/services/auth_service.py` | Service | Login, registration, token refresh, session management, security events |
