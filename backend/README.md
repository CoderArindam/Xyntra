# KAIO Backend API

This is the backend API for KAIO, built using **FastAPI**, **PostgreSQL**, and **Playwright**. It provides the core data services, business logic, an AI orchestration assistant, and meeting automation features.

---

## High-Level Folder Structure

```text
backend/
├── .env                       # Local environment variables configuration
├── requirements.txt           # Python application dependencies
├── uploads/                   # Media directory for board and task attachments
├── storage/                   # Backup and local persistence directory
├── app/                       # Main application package
│   ├── main.py                # Main FastAPI entry point & app configuration
│   │
│   ├── ai/                    # Custom agentic AI assistant module
│   ├── auth/                  # Middleware and helpers for user sessions and JWT token validation
│   ├── config/                # Global configuration module (pydantic-settings)
│   ├── constants/             # Constant definitions and static values
│   ├── database/              # PostgreSQL database initialization and operations
│   ├── meeting/               # Isolated meeting automation module
│   ├── routers/               # 17 REST API route handlers (auth, boards, tasks, comments, attachments, activity, board_members, admin, invitations, notifications, my_work, preferences, organization, ai, task_proposals, meeting)
│   ├── schemas/               # Request validation & response DTO schemas
│   └── services/              # Transactional business logic implementation layer
```

---

## Architecture & Subsystem Highlights

### 1. Main Entry & Dependency Injection
The app is initialized in `main.py` using Uvicorn. FastAPI's Dependency Injection system is extensively used to inject database connections and current user sessions into endpoints (e.g. `Depends(get_db_connection)`, `Depends(get_current_user)`). 
CORS middleware handles cross-origin requests, and static media is mounted at `/uploads`.

### 2. Configuration Strategy
Configuration across the backend relies heavily on `pydantic-settings`. 
Each major subsystem manages its own `.env` schema (e.g. `Settings`, `AISettings`, `MeetingSettings` with prefixed variables) ensuring strong typing, validation, and domain separation.

### 3. Database Architecture ([app/database](file:///d:/kanban-project/backend/app/database))
The database uses `asyncpg` for high-performance, asynchronous PostgreSQL connectivity across 35 migration scripts (`001_*.sql` to `035_*.sql`).
* **Connection Pooling**: Managed via `asyncpg.create_pool` with configurable min/max sizing.
* **JSON Codecs**: Custom codecs are bound to parse `json` and `jsonb` natively to Python dicts.
> [!IMPORTANT]
> **Database Rules**: Do NOT use raw SQL queries (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) in routers or services. All persistence must go through PostgreSQL user-defined functions (UDFs) or canonical views (`v_..._canonical`). This enforces database-level encapsulation.

### 4. Authentication & Security Subsystem ([app/auth](file:///d:/kanban-project/backend/app/auth))
* **JWT Tokens**: Authentication relies on robust stateless JWT access tokens and refresh tokens.
* **Multi-Device Sessions**: Tracks active sessions in `active_sessions` database table with user agent and IP address (`fn_refresh_session`, `fn_revoke_session`).
* **Security Event Logging**: Audit log (`fn_log_security_event`) tracking logins, logouts, session revocations, password updates, and role modifications.
* **Hashing**: Passwords are one-way hashed using `bcrypt` (via `passlib`).

### 5. AI Subassistant: [app/ai](file:///d:/kanban-project/backend/app/ai)
A custom AI agent system designed to interact with Kanban workspaces. It receives user prompts, routes intents, plans a chain of actions, and executes tools directly on the workspace.
* *For details on how planning, execution, and LLM providers are configured, see the [AI Subsystem README](file:///d:/kanban-project/backend/app/ai/README.md).*

### 6. Meeting Subassistant: [app/meeting](file:///d:/kanban-project/backend/app/meeting)
An isolated module designed to join online video meetings via a Playwright browser instance, record audio, transcribe the dialogue, extract task items, and automatically insert them onto boards.
* *For details on browser concurrency, error handling, and orchestration, see the [Meeting Subsystem README](file:///d:/kanban-project/backend/app/meeting/README.md).*
