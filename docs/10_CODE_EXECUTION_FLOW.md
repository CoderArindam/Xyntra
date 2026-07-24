# 10 — Code Execution Flow

## 1. Executive Summary

This document contains Mermaid sequence diagrams tracing key user interactions and system execution paths across KAIO.

> [!IMPORTANT]
> All authenticated requests use **httpOnly cookie-based auth**. The `access_token` cookie is automatically sent with every request — no `Authorization` header attachment in the frontend code.

---

## 2. Sequence Diagram 1: User Login Flow (with Cookie Auth & Security Logging)

```mermaid
sequenceDiagram
    autonumber
    participant User as React SPA (authStore)
    participant API as /api/v1/auth/login
    participant Service as AuthService
    participant DB as PostgreSQL DB

    User->>API: POST /api/v1/auth/login {email, password}
    API->>Service: auth_service.login(user_in, ua_string, ip_address)
    Service->>DB: SELECT * FROM v_users_canonical WHERE email = $1
    DB-->>Service: User Record (Hashed Password)
    Service->>Service: Verify Password (bcrypt)
    Service->>DB: SELECT fn_refresh_session(user_id, token, user_agent, ip)
    DB-->>Service: Active Session Record
    Service->>DB: SELECT fn_log_security_event(user_id, 'user_login', ip, user_agent)
    DB-->>Service: Event Logged
    API->>API: Set access_token cookie (15 min, httpOnly)
    API->>API: Set refresh_token cookie (7 days, httpOnly, path=/api/v1/auth)
    API-->>User: 200 OK {message: "Login successful"}
    User->>API: GET /api/v1/auth/me (cookie sent automatically)
    API-->>User: UserResponse {id, email, role, organization_id, ...}
    User->>User: authStore.set({isAuthenticated: true, user})
```

---

## 3. Sequence Diagram 2: Protected Route Access & Session Validation

```mermaid
sequenceDiagram
    autonumber
    participant Browser as Browser (React SPA)
    participant Axios as Axios (withCredentials: true)
    participant Auth as get_current_user dependency
    participant DB as PostgreSQL DB

    Browser->>Axios: Request to protected endpoint (cookie auto-attached)
    Axios->>Auth: Cookie: access_token=<JWT>
    Auth->>Auth: verify_token(cookie_value) — decode JWT
    Auth->>DB: SELECT fn_is_session_revoked(session_id)
    DB-->>Auth: false (session active)
    Auth-->>Axios: {id, email, role, organization_id, session_id}
    Axios-->>Browser: 200 OK with response data

    note over Browser,DB: If fn_is_session_revoked returns true:
    Auth->>Axios: 401 Unauthorized
    Axios->>Browser: Response interceptor: authStore.logout({forced: true})
    Browser->>Browser: Redirect to /login, toast "Session expired"
```

---

## 4. Sequence Diagram 3: Kanban Board Loading & Card Rendering

```mermaid
sequenceDiagram
    autonumber
    participant User as React SPA (BoardPage)
    participant API as /api/v1/boards/{id}
    participant DB as PostgreSQL DB

    User->>API: GET /api/v1/boards/{id} (access_token cookie)
    API->>DB: SELECT * FROM v_boards_canonical WHERE id = $1
    DB-->>API: Board Record (name, description, member count)
    API->>DB: SELECT * FROM v_tasks_canonical WHERE board_id = $1
    DB-->>API: Task Cards List (with assignee, priority, due date, column_id)
    API-->>User: 200 OK {board, columns, tasks}
    User->>User: taskStore.setBoard(board, columns, tasks)
    User->>User: KanbanBoard renders @dnd-kit columns + TaskCards
```

---

## 5. Sequence Diagram 4: Drag-and-Drop Task Move

```mermaid
sequenceDiagram
    autonumber
    participant User as React SPA (KanbanBoard)
    participant Store as taskStore (Zustand)
    participant API as /api/v1/tasks/{id}/move
    participant DB as PostgreSQL DB

    User->>Store: onDragEnd event — compute new column_id + position
    Store->>Store: Optimistic UI update (reorder tasks in store)
    Store->>API: POST /api/v1/tasks/{id}/move {column_id, position}
    API->>DB: SELECT fn_move_task(task_id, new_column_id, new_position)
    DB-->>API: Updated Task Record
    API-->>Store: 200 OK
    note over Store: On failure: rollback optimistic update
```

---

## 6. Sequence Diagram 5: Meeting Join & Recording Launch

```mermaid
sequenceDiagram
    autonumber
    participant User as React SPA
    participant API as Meeting API Router
    participant Service as MeetingService
    participant Bot as Playwright Bot Controller
    participant Rec as MeetingRecorder

    User->>API: POST /api/v1/meeting/join {meeting_url}
    API->>Service: join_meeting(meeting_url)
    Service->>Service: Create MeetingRuntime Instance
    Service->>Bot: launch_browser() & navigate(meeting_url)
    Bot->>Bot: Bypass Google Auth & Join Room
    Bot->>Rec: start_recording()
    Rec->>Rec: Inject capture_script.js & start MediaRecorder
    Rec-->>Service: Recording Active
    Service-->>API: Session ID & Status JOINED
    API-->>User: 200 OK {session_id, status: "JOINED"}
```

---

## 7. Sequence Diagram 6: Meeting Teardown, Audio Flush & Pipeline Processing

```mermaid
sequenceDiagram
    autonumber
    participant User as React SPA
    participant API as Meeting API Router
    participant Service as MeetingService
    participant Rec as MeetingRecorder
    participant Orchestrator as MeetingPipelineOrchestrator
    participant Deepgram as Deepgram Nova-3 API
    participant Engine as Dynamic Attribution Engine

    User->>API: POST /api/v1/meeting/leave
    API->>Service: leave_meeting(session_id)
    Service->>Rec: stop_recording()
    Rec->>Rec: Flush WebM byte chunks
    Rec-->>Service: Save storage/meeting/recordings/{id}/recording.webm
    Service->>Orchestrator: execute_pipeline(session_id)

    rect rgb(240, 240, 240)
        Note over Orchestrator: Stage 1: FFmpeg audio preprocessing → processed_audio.wav
        Note over Orchestrator: Stage 2: Participant presence collection
        Orchestrator->>Deepgram: Stage 3&4: POST /v1/listen?model=nova-3&diarize=true
        Deepgram-->>Orchestrator: RawTranscript + SpeakerTurns
        Orchestrator->>Engine: Stage 5&6: Speaker alignment + identity resolution
        Engine-->>Orchestrator: participant_attributed_transcript.json
        Note over Orchestrator: Stage 7: LLM task extraction → fn_create_task_proposal
    end

    Orchestrator-->>Service: Pipeline Complete (PROPOSALS_READY)
    Service->>Service: NotificationService.notify_managers()
    Service-->>API: Attributed Transcript JSON
    API-->>User: 200 OK (session status: PROPOSALS_READY)
```

---

## 8. Sequence Diagram 7: AI Task Proposal Approval & Task Creation

```mermaid
sequenceDiagram
    autonumber
    participant Manager as Manager / Admin SPA
    participant API as /api/v1/proposals/{id}/approve
    participant Auth as require_proposal_review_access
    participant DB as PostgreSQL DB
    participant Notif as NotificationService

    Manager->>API: POST /api/v1/proposals/{id}/approve {board_id: "..."}
    API->>Auth: fn_check_proposal_review_access(user_id, org_id)
    Auth->>DB: SELECT fn_check_proposal_review_access($1, $2)
    DB-->>Auth: true (Authorized)
    API->>DB: SELECT * FROM fn_approve_task_proposal(proposal_id, board_id, user_id)
    DB-->>API: Created Task Record
    API->>Notif: notify_proposal_approved(proposal, created_task)
    Notif->>DB: SELECT fn_create_notification(...)
    DB-->>Notif: Notification Record Created
    API-->>Manager: 200 OK {task: CreatedTask}
```

---

## 9. Sequence Diagram 8: Invitation Send & Accept Flow

```mermaid
sequenceDiagram
    autonumber
    participant Manager as Manager SPA
    participant API as /api/v1/invitations
    participant Service as InvitationService
    participant Email as Email Service (SMTP)
    participant Invitee as Invitee Browser

    Manager->>API: POST /api/v1/invitations {email, role} (Manager+ required)
    API->>Service: invitation_service.invite_user(invite_in, current_user)
    Service->>Service: Generate secure token, store in organization_invitations
    Service-->>API: {invitation, email, org_name, token}
    API->>Email: background_tasks.add_task(send_invitation_email, email, org_name, token)
    Email-->>Invitee: Email with invite link /accept-invitation?token=<TOKEN>
    API-->>Manager: 201 Created (InvitationResponse)

    Invitee->>API: GET /api/v1/invitations/verify/{token}
    API-->>Invitee: {email, org_name, role} (invitation details)
    Invitee->>API: POST /api/v1/invitations/accept {token, password, first_name, last_name}
    API->>Service: invitation_service.accept_invitation(body)
    Service->>Service: Create user account, mark invitation accepted_at
    API-->>Invitee: {message: "Account created successfully. You can now log in."}
```

---

## 10. Sequence Diagram 9: Invitation Revocation Flow

```mermaid
sequenceDiagram
    autonumber
    participant Manager as Manager SPA (Organization Settings)
    participant API as /api/v1/invitations/{id}
    participant Service as InvitationService
    participant DB as PostgreSQL DB

    Manager->>API: DELETE /api/v1/invitations/{invitation_id} (Manager+ required)
    API->>Service: invitation_service.revoke_invitation(invitation_id, current_user)
    Service->>DB: SELECT revoke_invitation(p_invitation_id, p_org_id)
    DB->>DB: DELETE FROM organization_invitations WHERE id=$1 AND accepted_at IS NULL
    DB-->>Service: Deleted invitation JSON
    Service-->>API: Success
    API-->>Manager: 204 No Content
```

---

## 11. Sequence Diagram 10: Dashboard Data Loading (Manager/Superadmin)

```mermaid
sequenceDiagram
    autonumber
    participant Manager as Manager SPA (DashboardView)
    participant API as /api/v1/dashboard/summary
    participant Auth as require_proposal_review_access
    participant Service as DashboardService
    participant DB as PostgreSQL DB

    Manager->>API: GET /api/v1/dashboard/summary (access_token cookie)
    API->>Auth: fn_check_proposal_review_access(user_id, org_id)
    DB-->>Auth: true (Manager or Superadmin)
    API->>Service: dashboard_service.get_dashboard_summary(current_user)
    Service->>DB: SELECT * FROM v_dashboard_kpis_canonical WHERE organization_id = $1
    DB-->>Service: KPI row (totals, by-status, overdue, pending proposals, etc.)
    Service->>DB: SELECT * FROM v_dashboard_board_summaries_canonical WHERE organization_id = $1
    DB-->>Service: Board summary rows (per-board task counts, completion %)
    Service->>DB: SELECT * FROM v_activities_canonical WHERE organization_id = $1 LIMIT 10
    DB-->>Service: Recent activity rows
    Service-->>API: DashboardSummaryResponse {kpis, boards, recent_activity}
    API-->>Manager: 200 OK {data: {kpis, boards, recent_activity}}
    Manager->>Manager: Render KpiCardsRow, BoardsOverviewWidget, RecentActivityWidget, etc.
```

---

## 12. Sequence Diagram 11: Timesheet Submission & Manager Approval Flow

```mermaid
sequenceDiagram
    autonumber
    participant Member as Member SPA (TimesheetWeekView)
    participant API as /api/v1/timesheets
    participant Manager as Manager SPA (ApprovalQueuePage)
    participant DB as PostgreSQL DB
    participant Notif as Notification Service

    Member->>API: POST /api/v1/timesheets/{id}/entries (board_id, task_id, entry_date, hours, entry_type)
    API->>DB: SELECT * FROM fn_upsert_timesheet_entry(...)
    DB->>DB: Enforce task owner assignment check (if task linked)
    DB-->>API: TimesheetEntryResponse
    API-->>Member: 201 Created / Updated

    Member->>API: POST /api/v1/timesheets/{id}/submit {member_note, approver_id}
    API->>DB: SELECT * FROM fn_submit_timesheet(...)
    DB->>DB: Validate policy rules (deadlines, min hours, overtime lock) & update status to 'submitted'
    DB-->>API: Updated Timesheet Record
    API->>Notif: notify_timesheet_submitted(conn, timesheet_id, submitter_id, approver_id)
    Notif->>DB: SELECT fn_create_timesheet_notification(...)
    API-->>Member: 200 OK (TimesheetResponse status='submitted')

    Manager->>API: GET /api/v1/timesheets/approvals/queue
    API->>DB: SELECT * FROM v_timesheets_canonical WHERE org_id=$1 AND status='submitted'
    DB-->>API: Queue items
    API-->>Manager: 200 OK [ApprovalQueueItemResponse]

    Manager->>API: POST /api/v1/timesheets/{id}/approve {comment}
    API->>DB: SELECT * FROM fn_approve_timesheet(...)
    DB->>DB: Update status to 'approved', record reviewed_at & approver_id, lock timesheet
    DB-->>API: Updated Timesheet Record
    API->>Notif: notify_timesheet_approved(conn, timesheet_id, submitter_id, approver_id)
    Notif->>DB: SELECT fn_create_timesheet_notification(...)
    API-->>Manager: 200 OK (TimesheetResponse status='approved')
```

