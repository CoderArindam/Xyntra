# KAIO Meeting Automation Module

## Phase M0 — Architectural Foundation

This module provides the **meeting automation subsystem** for KAIO. It is designed to be **completely isolated** from the existing KAIO architecture (AI, workspaces, tasks, auth).

> **Current status:** Placeholder architecture only. No browser launches, no recording, no transcription, no AI processing.

---

## Technical Configuration & Environment

The meeting module uses environment-based configurations mapped through `pydantic-settings` ([config.py](file:///d:/kanban-project/backend/app/meeting/config.py)).

- **Environment Prefix**: All environment variables for this module must be prefixed with `MEETING_` (e.g., `MEETING_HEADLESS`, `MEETING_GOOGLE_EMAIL`).
- **Concurrency Limits**: Hard caps exist on the number of concurrently running Playwright instances (`MAX_CONCURRENT_SESSIONS=3`).
- **Fault Tolerance & Timeouts**:
  - Max session duration: 3600 seconds.
  - Wait time limits for landing pages (60s) and Google Auth flows (45s).
  - Auto screenshot dumps upon unexpected bot failure saved to `storage/meeting/debug`.
- **Heartbeat Monitoring**: The bot ticks every 5 seconds to assert the stability of the browser connection and page state.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Meeting API                     │
│          POST /join · POST /leave                │
│              GET /session/{id}                   │
└──────────────────┬──────────────────────────────┘
                   │
         ┌─────────▼──────────┐
         │   MeetingService    │   ← Orchestration layer
         └──┬──────┬──────┬───┘
            │      │      │
   ┌────────▼┐  ┌──▼────┐ ┌▼──────────┐
   │ Session  │  │  Bot  │ │ Recorder   │
   │ Manager  │  │(Join/ │ │(Audio/     │
   │          │  │ Leave)│ │ Video)     │
   └──────────┘  └──┬────┘ └───────────┘
                    │
            ┌───────▼────────┐
            │ BrowserController│   ← Playwright wrapper
            └────────────────┘

┌─────────────────────────────────────────────────┐
│              Downstream Pipelines                │
│  TranscriptionPipeline → TaskExtractionPipeline  │
│                    → AssignmentEngine            │
└─────────────────────────────────────────────────┘
```

---

## Folder Structure

```
backend/app/meeting/
├── __init__.py
├── config.py               # Meeting-specific configuration
├── README.md
│
├── api/
│   ├── __init__.py
│   └── router.py           # FastAPI router (3 endpoints)
│
├── bot/
│   ├── browser/
│   │   ├── __init__.py
│   │   └── controller.py   # BrowserController (Playwright stub)
│   ├── joiner/
│   │   ├── __init__.py
│   │   └── bot.py          # MeetingBot (join/leave)
│   ├── session/
│   │   ├── __init__.py
│   │   └── manager.py      # MeetingSessionManager
│   ├── recorder/
│   │   ├── __init__.py
│   │   └── recorder.py     # MeetingRecorder (stub)
│   └── audio/
│       └── __init__.py
│
├── transcription/
│   ├── __init__.py
│   └── pipeline.py         # TranscriptionPipeline (stub)
│
├── extraction/
│   ├── __init__.py
│   └── pipeline.py         # TaskExtractionPipeline (stub)
│
├── assignment/
│   ├── __init__.py
│   └── engine.py           # AssignmentEngine (stub)
│
├── pipelines/
│   └── __init__.py
│
├── models/
│   ├── __init__.py
│   └── session.py          # MeetingSession dataclass (in-memory)
│
├── schemas/
│   ├── __init__.py
│   └── meeting.py          # Pydantic request/response schemas
│
├── services/
│   ├── __init__.py
│   └── meeting_service.py  # MeetingService (orchestration)
│
└── utils/
    └── __init__.py
```

---

## Component Responsibilities

| Component                  | Responsibility                                                                    |
| -------------------------- | --------------------------------------------------------------------------------- |
| **MeetingService**         | Top-level orchestration. Coordinates all meeting components.                      |
| **MeetingSessionManager**  | Creates, tracks, ends, and cleans up in-memory sessions.                          |
| **MeetingBot**             | Joins/leaves meetings via browser automation.                                     |
| **BrowserController**      | Low-level Playwright browser lifecycle management with isolated context profiles. |
| **MeetingRecorder**        | Audio/video capture from browser tab.                                             |
| **TranscriptionPipeline**  | Speech-to-text processing.                                                        |
| **TaskExtractionPipeline** | LLM-powered action item extraction from transcripts.                              |
| **AssignmentEngine**       | Maps extracted tasks to workspace members and creates Kanban tasks.               |

---

## Data Flow (Future)

```
Meeting URL
    → MeetingBot.join()
    → BrowserController (Playwright)
    → MeetingRecorder (audio capture)
    → TranscriptionPipeline (speech-to-text)
    → TaskExtractionPipeline (LLM extraction)
    → AssignmentEngine (task creation)
    → KAIO Kanban Board
```

---

## API Endpoints

| Method | Path                           | Description                   |
| ------ | ------------------------------ | ----------------------------- |
| `POST` | `/api/v1/meeting/join`         | Accept a meeting join request |
| `POST` | `/api/v1/meeting/leave`        | End a meeting session         |
| `GET`  | `/api/v1/meeting/session/{id}` | Get session details           |

---

## Dependency Isolation

This module has **zero imports** from:

- `app.ai.*`
- `app.services.*`
- `app.routers.*`
- `app.auth.*`
- `app.database.*`

All dependencies are internal to `app.meeting.*`.

---

## Logging

All loggers use the `meeting.*` namespace:

- `meeting.api`
- `meeting.service`
- `meeting.session`
- `meeting.bot.joiner`
- `meeting.bot.browser`
- `meeting.bot.recorder`
- `meeting.transcription`
- `meeting.extraction`
- `meeting.assignment`

---

## Future Phases

| Phase     | Scope                                        |
| --------- | -------------------------------------------- | --- |
| **M0** ✅ | Architecture, placeholders, API stubs        |
| **M1** ✅ | Playwright browser launch + Google Meet join |     |
| **M2**    | Audio capture + transcription pipeline       |
| **M3**    | LLM task extraction from transcripts         |
| **M4**    | Task assignment + Kanban integration         |
| **M5**    | Google Calendar integration                  |
