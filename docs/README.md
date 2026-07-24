# KAIO Architectural & Technical Documentation Suite

Welcome to the official, complete technical documentation suite for **KAIO** (Kanban AI Orchestration). This documentation is specifically structured to act as a comprehensive, zero-loss **AI Context Package** for senior software architects, engineering teams, and AI code assistants (such as ChatGPT, Claude, Gemini, and similar).

---

## 📑 Documentation Index

| # | Document | Primary Focus & Content Summary |
|---|---|---|
| **01** | [Project Overview](./01_PROJECT_OVERVIEW.md) | Business objectives, core USP, high-level system architecture diagram, current implementation status (Phases 1.0 through 4.0 complete including Timesheet Engine), and roadmap. |
| **02** | [Backend Architecture](./02_BACKEND_ARCHITECTURE.md) | FastAPI framework design, **21 REST API routers** (including Timesheets, Approvals & Admin), httpOnly cookie auth, RBAC layers, strict stored-procedure DB rule, service layer catalog, meeting orchestrator, dashboard service, and invitation service. |
| **03** | [Frontend Architecture](./03_FRONTEND_ARCHITECTURE.md) | **React 19** + Vite + **Tailwind CSS v4** frontend structure, **Zustand v5** state management (10 stores), React Router v7, @dnd-kit drag-and-drop, route guards (ProtectedRoute + RequireRole), **13 feature modules** (including Timesheets), **21 API service files**. |
| **04** | [Database Architecture](./04_DATABASE_ARCHITECTURE.md) | PostgreSQL schema across **47 migrations**, canonical views (`v_*_canonical`), stored functions (`fn_*`), ERD with all entities (including Timesheets & Policies), RLS/authz functions, session tables, dashboard views, invitation revocation function. |
| **05** | [Meeting Pipeline](./05_MEETING_PIPELINE.md) | Deep dive into post-processing meeting automation: Playwright bot, PulseAudio/FFmpeg audio recording, Deepgram STT/Diarization, Speaker Attribution, and AI Task Extraction with notification dispatch. |
| **06** | [AI Architecture](./06_AI_ARCHITECTURE.md) | Deepgram speech provider, Puter/Gemini LLM integrations, KAI AI agent (chat + tools), clarification router, AI Task Extraction pipeline, and action item proposal flows. |
| **07** | [API Reference](./07_API_REFERENCE.md) | Complete REST API endpoint documentation covering **all 23 router sections**: auth (cookies), boards, tasks, comments, activity, invitations, organization, admin, my-work, preferences, users, dashboard, meeting, presence, proposals, timesheets, timesheet approvals, and timesheet admin/policy. |
| **08** | [Component Reference](./08_COMPONENT_REFERENCE.md) | Frontend component catalog: paths, props, responsibilities. Covers shared UI, layout, board/kanban, **9 dashboard widgets**, timesheet grid & approvals, admin panel, notifications, settings, auth, my-work, and project settings. |
| **09** | [Folder Reference](./09_FOLDER_REFERENCE.md) | Comprehensive directory dictionary mapping every folder in `backend`, `frontend`, `database`, and `extension` to its purpose, key files, and dependencies. |
| **10** | [Code Execution Flow](./10_CODE_EXECUTION_FLOW.md) | **11 Mermaid sequence diagrams** for: login (cookie auth), session validation, board loading, drag-and-drop move, meeting recording, audio pipeline, proposal approval, invitation send/accept, invitation revocation, dashboard loading, and timesheet submission/approval. |
| **11** | [Configuration Reference](./11_CONFIGURATION_REFERENCE.md) | Environment configuration guide covering `settings.py` vars, cookie auth settings, meeting config, AI/LLM config, CORS, and startup commands. |
| **12** | [Glossary](./12_GLOSSARY.md) | Authoritative glossary defining all domain-specific terminology: httpOnly cookie auth, Zustand stores, RBAC roles, board columns, canonical views, invitations, security events, meeting sessions, timesheets, timesheet policies, and more. |
| **13** | [Chrome Extension Architecture](./13_CHROME_EXTENSION_ARCHITECTURE.md) | Dedicated guide to the Manifest V3 Chrome Extension: DOM observers, MutationObserver, background service worker, and real-time backend presence event dispatch. |
| **14** | [VPS Meeting Bot Deployment](./14_VPS_MEETING_BOT_DEPLOYMENT.md) | Complete Linux VPS deployment guide for KAIO Meeting Bot: Chromium, Playwright, FFmpeg, PulseAudio/PipeWire virtual audio sink (`kaio_sink`), Xvfb frame buffer, startup/shutdown scripts, systemd unit, and health check diagnostics. |

---

## 🤖 Instructions for AI Assistants (Context Onboarding)

If you are an AI assistant tasked with answering questions, adding features, or debugging KAIO, follow this onboarding checklist:

### Step 1 — Read Architecture Documents
1. **`01_PROJECT_OVERVIEW.md`** — Understand the system, tech stack, and current phase.
2. **`02_BACKEND_ARCHITECTURE.md`** — Read the DB rule, router list, auth mechanism, and service catalog.
3. **`03_FRONTEND_ARCHITECTURE.md`** — Understand Zustand stores, feature structure, and cookie auth.
4. **`04_DATABASE_ARCHITECTURE.md`** — Learn canonical views, stored functions, and migration list.

### Step 2 — Critical Rules to Never Violate

> [!CAUTION]
> **Rule 1 — No Inline SQL**: Backend Python routers and services **MUST NEVER** write raw SQL (`SELECT`, `INSERT`, `UPDATE`, `DELETE`). All reads go through `v_*_canonical` views. All writes call `fn_*` stored procedures.

> [!CAUTION]
> **Rule 2 — Cookie Auth**: The auth system uses **httpOnly cookies** (`access_token`, `refresh_token`). Do NOT add `Authorization: Bearer` header logic to the frontend. Do NOT return tokens in response bodies. Use `withCredentials: true` on Axios.

> [!CAUTION]
> **Rule 3 — Zustand, not Context**: The frontend uses **Zustand v5** stores for all global state. Do NOT create React Context providers for global state. Use the appropriate existing store.

> [!CAUTION]
> **Rule 4 — React 19 + Tailwind v4**: The frontend is on React 19 and Tailwind CSS v4 (no `tailwind.config.js` — configured via CSS). Do not downgrade or introduce v3 patterns.

### Step 3 — Find Your Feature
- Use **`07_API_REFERENCE.md`** to look up backend endpoints.
- Use **`08_COMPONENT_REFERENCE.md`** to find frontend components.
- Use **`09_FOLDER_REFERENCE.md`** to locate files.
- Use **`10_CODE_EXECUTION_FLOW.md`** to trace request/response paths.

### Step 4 — User Credentials (Dev/Testing)
See **`USER_CREDENTIALS.md`** for seeded login credentials for both TechInnovators India and DevArc workspaces.
