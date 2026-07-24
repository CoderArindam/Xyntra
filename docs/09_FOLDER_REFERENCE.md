# 09 — Folder Reference

## 1. Executive Summary

This directory dictionary maps every major folder across the repository, explaining its purpose, primary contents, dependencies, and key entry points.

---

## 2. Root Level

| Path | Purpose | Key Files |
|---|---|---|
| `backend/` | FastAPI Python backend application | `app/main.py`, `.env`, `requirements.txt` |
| `database/` | PostgreSQL schema migrations & rebuild scripts | `migrations/`, `scripts/rebuild.py` |
| `deploy/` | Linux VPS deployment & meeting bot environment scripts | `deploy/vps/install_dependencies.sh`, `start_meeting_bot_env.sh`, `health_check.sh` |
| `docs/` | Architecture documentation suite for AI agents & engineers | `README.md`, `01_PROJECT_OVERVIEW.md` … `14_VPS_MEETING_BOT_DEPLOYMENT.md` |
| `extension/` | Manifest V3 Chrome Extension for presence tracking | `manifest.json`, `content/`, `background/` |
| `frontend/` | React 19 + Vite single-page application | `src/main.tsx`, `vite.config.ts`, `package.json` |

---

## 3. Backend Directory (`backend/`)

| Path | Purpose | Key Files | Dependencies |
|---|---|---|---|
| `backend/app/` | Core FastAPI application root | `main.py` | FastAPI, asyncpg, Pydantic v2 |
| `backend/app/ai/` | LLM integration: KAI agent, Puter/Gemini providers, clarification router, orchestration | `provider.py`, `agents/`, `orchestration/`, `tools/`, `prompts/`, `context/`, `telemetry/` | Puter SDK, Gemini API, httpx |
| `backend/app/auth/` | JWT auth, multi-device sessions, RBAC permission guards | `dependencies.py`, `jwt.py`, `password.py`, `permissions.py` | PyJWT[crypto], Passlib, bcrypt |
| `backend/app/config/` | Application environment settings loaded via pydantic-settings | `settings.py` | pydantic-settings |
| `backend/app/constants/` | System-wide constants and enums | — | — |
| `backend/app/database/` | asyncpg connection pool manager and DB dependency | `connection.py` | asyncpg |
| `backend/app/meeting/` | Full meeting pipeline subsystem | `api/router.py`, `services/meeting_service.py` | Playwright, Deepgram SDK, FFmpeg |
| `backend/app/meeting/api/` | Meeting HTTP router endpoints | `router.py` | FastAPI |
| `backend/app/meeting/bot/` | Playwright browser automation + JS injection | `recorder/recorder.py`, `recorder/capture_script.py` | Playwright Chromium |
| `backend/app/meeting/pipeline/` | Sequential post-processing stage engine + task extraction | `orchestrator.py`, `stages/`, `context.py` | Deepgram, FFmpeg, LLM |
| `backend/app/meeting/providers/` | Speech (Deepgram) and presence providers | `speech/deepgram_provider.py`, `participant_presence/` | Deepgram SDK, asyncpg |
| `backend/app/routers/` | **21** REST API endpoint handler modules | `auth.py`, `boards.py`, `tasks.py`, `comments.py`, `notifications.py`, `invitations.py`, `dashboard.py`, `admin.py`, `task_proposals.py`, `timesheets.py`, `timesheet_approvals.py`, `timesheet_admin.py`, `timesheet_errors.py`, etc. | FastAPI, Pydantic |
| `backend/app/schemas/` | Pydantic v2 request/response DTO schemas | `auth.py`, `board.py`, `task.py`, `task_proposal.py`, `dashboard.py`, `invitations.py`, `timesheets.py`, `timesheet_approvals.py`, `timesheet_admin.py`, etc. | Pydantic v2 |
| `backend/app/services/` | Business logic services (one per domain) | `auth_service.py`, `board_service.py`, `task_service.py`, `dashboard_service.py`, `invitation_service.py`, `notification_service.py`, `email_service.py`, etc. | asyncpg, httpx |
| `backend/storage/` | Local disk file storage for meeting artifacts | `meeting/recordings/`, `meeting/processed_audio/` | OS filesystem |
| `backend/uploads/` | Uploaded task attachment files (served as static at `/uploads/`) | `.webm`, `.png`, `.pdf`, etc. | FastAPI StaticFiles |
| `backend/archive/` | Archived/legacy scripts & CLI tools | `tools/` | — |
| `backend/tests/` | Pytest automated test suites | `test_*.py` | pytest, httpx |

---

## 4. Database Directory (`database/`)

| Path | Purpose | Key Files | Dependencies |
|---|---|---|---|
| `database/migrations/` | **47** sequential `.sql` migration files | `001_extensions.sql` … `047_fix_rejected_timesheet_status.sql` | PostgreSQL 15+ |
| `database/scripts/` | Database rebuild & maintenance scripts | `rebuild.py` | asyncpg, python-dotenv |

**Rebuild command**:
```powershell
# Incremental (safe, no data loss)
python database/scripts/rebuild.py

# Full reset (drops and recreates schema)
python database/scripts/rebuild.py --reset
```

---

## 5. Frontend Directory (`frontend/`)

| Path | Purpose | Key Files | Dependencies |
|---|---|---|---|
| `frontend/src/app/` | Application root — router setup and app entry wiring | `App.tsx` or equivalent | React Router DOM v7 |
| `frontend/src/assets/` | Static graphics, SVG icons, logos | `*.svg`, `*.png` | — |
| `frontend/src/components/common/` | Reusable domain-agnostic components (modals, avatars, empty states) | `Modal.tsx`, `UserAvatar.tsx`, `ConfirmDialog.tsx`, etc. | React 19, Lucide React |
| `frontend/src/components/layout/` | Application shell layout components | `AppLayout.tsx`, `ApplicationSidebar.tsx`, `SettingsLayout.tsx`, `UserAvatarDropdown.tsx` | React Router DOM v7, Zustand |
| `frontend/src/components/shared/` | Reusable domain-specific selector inputs | `AssigneeSelector.tsx`, `DueDatePicker.tsx`, `PrioritySelector.tsx`, `StatusSelector.tsx` | React 19 |
| `frontend/src/components/ui/` | Low-level primitive UI components | `Button.tsx`, `Card.tsx`, `Skeleton.tsx`, `WidgetError.tsx` | Tailwind CSS v4 |
| `frontend/src/constants/` | Application constants, route path definitions | `routes.ts`, `config.ts` | — |
| `frontend/src/features/` | Feature-scoped page modules (13 features) | `auth/`, `boards/`, `dashboard/`, `admin/`, `settings/`, `my-work/`, `meeting/`, `notifications/`, `proposals/`, `projects/`, `activity/`, `ai/`, `timesheets/` | React 19, Zustand, Axios |
| `frontend/src/hooks/` | Custom React hooks | `useDebounce.ts`, `usePageTitle.ts` | React 19 |
| `frontend/src/lib/` | Axios instance configuration with interceptors | `axios.ts` or similar | Axios v1 |
| `frontend/src/routes/` | React Router route guard components | `ProtectedRoute.tsx`, `RequireRole.tsx` | React Router DOM v7, Zustand |
| `frontend/src/services/` | API call functions (21 service files, one per domain) | `authApi.ts`, `boardsApi.ts`, `tasksApi.ts`, `dashboardApi.ts`, `timesheetService.ts`, `timesheetApprovalService.ts`, `timesheetAdminService.ts`, `timesheetReportsApi.ts`, etc. | Axios v1 |
| `frontend/src/store/` | Zustand v5 global state stores (10 stores) | `authStore.ts`, `boardStore.ts`, `taskStore.ts`, `adminStore.ts`, `notificationStore.ts`, `organizationStore.ts`, `preferencesStore.ts`, `projectSettingsStore.ts`, `activityStore.ts`, `uiStore.ts` | Zustand v5 |
| `frontend/src/styles/` | Global CSS and Tailwind v4 customizations | `*.css` | Tailwind CSS v4 |
| `frontend/src/utils/` | Utility helper functions | `*.ts` | — |

---

## 6. Extension Directory (`extension/`)

| Path | Purpose | Key Files |
|---|---|---|
| `extension/manifest.json` | Manifest V3 configuration — permissions, host permissions, content scripts | — |
| `extension/background/` | Background service worker — event queuing, HTTP dispatch to backend | `service_worker.js` |
| `extension/content/` | Content scripts — Google Meet DOM observer | `GoogleMeetDOMAdapter.js`, `meet_observer.js` |
| `extension/options/` | Extension settings UI page | `options.html`, `options.js` |
| `extension/shared/` | Shared event type constants | `types.js` |

---

## 7. Docs Directory (`docs/`)

| Document | Content Summary |
|---|---|
| `README.md` | Documentation index and AI agent onboarding instructions |
| `01_PROJECT_OVERVIEW.md` | Business objectives, USP, system architecture, phase roadmap |
| `02_BACKEND_ARCHITECTURE.md` | FastAPI, 18 routers, services, auth (httpOnly cookies), RBAC layers, DB rule |
| `03_FRONTEND_ARCHITECTURE.md` | React 19, Zustand, Tailwind v4, feature structure, component tree, route guards |
| `04_DATABASE_ARCHITECTURE.md` | 37 migrations, ERD, canonical views, stored functions catalog |
| `05_MEETING_PIPELINE.md` | Bot join → WebM → FFmpeg → Deepgram → Attribution → Task Extraction pipeline |
| `06_AI_ARCHITECTURE.md` | Deepgram speech tier, Puter/Gemini LLM tier, KAI agent, extraction pipeline |
| `07_API_REFERENCE.md` | All 20 REST API sections — auth, boards, tasks, comments, invitations, admin, dashboard, etc. |
| `08_COMPONENT_REFERENCE.md` | Frontend component catalog — paths, props, purpose |
| `09_FOLDER_REFERENCE.md` | This document — full directory dictionary |
| `10_CODE_EXECUTION_FLOW.md` | Sequence diagrams for all key flows |
| `11_CONFIGURATION_REFERENCE.md` | Environment variables and config settings |
| `12_GLOSSARY.md` | Domain terminology definitions |
| `13_CHROME_EXTENSION_ARCHITECTURE.md` | Chrome extension DOM observer and presence dispatch |
| `USER_CREDENTIALS.md` | Seeded organization login credentials for development |
| `KAIO_Timesheet_Phases_and_Prompts.md` | Detailed phase-by-phase development plan and AI prompt suite |
