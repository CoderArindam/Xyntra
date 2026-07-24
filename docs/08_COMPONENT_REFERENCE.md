# 08 — Component Reference

## 1. Executive Summary

This document provides a reference catalog of the primary React UI components within `frontend/src/`. Components are organized by their location in the directory structure.

---

## 2. Shared UI Primitives (`src/components/ui/`)

| Component | Path | Description |
|---|---|---|
| `Button` | `components/ui/Button.tsx` | Styled button with variant support (primary, secondary, danger). |
| `Card` | `components/ui/Card.tsx` | Content card wrapper with consistent shadow and border styling. |
| `Skeleton` | `components/ui/Skeleton.tsx` | Loading skeleton placeholder for async content blocks. |
| `WidgetError` | `components/ui/WidgetError.tsx` | Error state display used inside dashboard widgets when data fetch fails. |

---

## 3. Shared Common Components (`src/components/common/`)

| Component | Path | Description |
|---|---|---|
| `Modal` | `components/common/Modal.tsx` | Accessible backdrop modal with slide-in animation, escape key dismissal, and close button. Props: `isOpen`, `onClose`, `title`, `children`. |
| `ConfirmDialog` | `components/common/ConfirmDialog.tsx` | Reusable confirmation prompt dialog for destructive actions (archive, delete, revoke). |
| `EmptyState` | `components/common/EmptyState.tsx` | Placeholder for empty lists with an icon, heading, and optional CTA button. |
| `ProjectCard` | `components/common/ProjectCard.tsx` | Board/project preview card with icon, color, name, and task count. |
| `ProjectIdentity` | `components/common/ProjectIdentity.tsx` | Renders board icon + color identity badge (used in headers and sidebars). |
| `UserAvatar` | `components/common/UserAvatar.tsx` | User avatar with image src or initials fallback, configurable size. |
| `WorkspaceLoader` | `components/common/WorkspaceLoader.tsx` | Full-page loading spinner shown during workspace initialization. |
| `WorkspaceLogo` | `components/common/WorkspaceLogo.tsx` | Organization logo/branding display with name fallback. |

---

## 4. Layout Components (`src/components/layout/`)

### 4.1 `AppLayout`
- **Path**: `components/layout/AppLayout.tsx`
- **Purpose**: Root application shell. Renders `ApplicationSidebar` + main content `<Outlet />`.

### 4.2 `ApplicationSidebar`
- **Path**: `components/layout/ApplicationSidebar.tsx`
- **Purpose**: Left navigation sidebar. Renders workspace logo, nav links (Dashboard, Boards, My Work, Meetings, Settings, Admin), notification bell, and active meeting status indicator. Collapses to icon-only mode.

### 4.3 `SettingsLayout`
- **Path**: `components/layout/SettingsLayout.tsx`
- **Purpose**: Layout wrapper for the Settings section. Renders a side tab list (My Account, Security, Appearance, Notifications, Organization) and the active tab's content via `<Outlet />`.

### 4.4 `UserAvatarDropdown`
- **Path**: `components/layout/UserAvatarDropdown.tsx`
- **Purpose**: Header user avatar menu — displays name/role, links to profile/settings, and logout action.

---

## 5. Shared Domain Selector Components (`src/components/shared/`)

| Component | Path | Description |
|---|---|---|
| `AssigneeSelector` | `components/shared/AssigneeSelector.tsx` | Dropdown for selecting a board member as task assignee. |
| `DueDatePicker` | `components/shared/DueDatePicker.tsx` | Date picker input for task due dates. |
| `PrioritySelector` | `components/shared/PrioritySelector.tsx` | Priority badge selector (LOW, MEDIUM, HIGH, URGENT). |
| `StatusSelector` | `components/shared/StatusSelector.tsx` | Column status selector for task editing. |

---

## 6. Kanban Board Feature (`src/features/boards/`)

### 6.1 `BoardPage`
- **Path**: `features/boards/BoardPage.tsx`
- **Purpose**: Page-level wrapper. Reads `boardId` from route params, fetches board data, renders `KanbanBoard` and header.

### 6.2 `KanbanBoard`
- **Path**: `features/boards/components/KanbanBoard.tsx`
- **Purpose**: Main drag-and-drop board workspace. Uses `@dnd-kit/core` `DndContext` + `@dnd-kit/sortable` for task card reordering across columns. Manages column rendering, filter state (assignee, due date), and optimistic UI updates.
- **Child Components**: Column containers (inline), `TaskCard`, filter bars.

### 6.3 `TaskCard`
- **Path**: `features/boards/components/TaskCard.tsx`
- **Purpose**: Draggable task card preview. Displays title, assignee avatar, due date, priority badge, and comment count. Clicking opens the task detail modal.

### 6.4 `AssigneeFilter`
- **Path**: `features/boards/components/AssigneeFilter.tsx`
- **Purpose**: Filter bar dropdown for filtering task cards by board member.

### 6.5 `DueDateFilter`
- **Path**: `features/boards/components/DueDateFilter.tsx`
- **Purpose**: Filter bar dropdown for filtering task cards by due date range (today, this week, overdue).

### 6.6 `CreateTaskModal`
- **Path**: `features/boards/modals/CreateTaskModal.tsx`
- **Purpose**: Quick task creation form with title, description, assignee selector, priority selector, and due date picker.

### 6.7 `AddMemberModal`
- **Path**: `features/boards/modals/AddMemberModal.tsx`
- **Purpose**: Modal for adding members to a board. Search by user email, set board role. Supports inviting new users to the workspace via the invitation flow.

### 6.8 `ArchiveProjectDialog`
- **Path**: `features/boards/modals/ArchiveProjectDialog.tsx`
- **Purpose**: Confirmation dialog for archiving (soft-deleting) a board project.

### 6.9 Task Detail Modals (`features/boards/modals/task-details/`)
- **Purpose**: Full task detail view. Displays and edits all task fields (title, description in Markdown, status, assignee, priority, due date), renders comment thread with replies, and shows file attachments.

---

## 7. Dashboard Feature (`src/features/dashboard/`)

> [!IMPORTANT]
> Only accessible to **Manager** and **Superadmin** roles. All data sourced from `GET /api/v1/dashboard/summary`.

### 7.1 `DashboardView`
- **Path**: `features/dashboard/DashboardView.tsx`
- **Purpose**: Orchestrates the full dashboard layout. Fetches data from `dashboardApi.ts` and distributes to child widgets.

### 7.2 `KpiCardsRow`
- **Path**: `features/dashboard/components/KpiCardsRow.tsx`
- **Purpose**: Top row of KPI metric cards — total tasks, tasks by status (todo/in-progress/review/done), overdue tasks, total boards, team size, pending proposals, active meetings.

### 7.3 `BoardsOverviewWidget`
- **Path**: `features/dashboard/components/BoardsOverviewWidget.tsx`
- **Purpose**: Grid of board progress cards — each shows board name, task count, completion percentage progress bar, and overdue count.

### 7.4 `StrategicProjectsWidget`
- **Path**: `features/dashboard/components/StrategicProjectsWidget.tsx`
- **Purpose**: Strategic project cards with visual progress indicators and health status.

### 7.5 `RecentActivityWidget`
- **Path**: `features/dashboard/components/RecentActivityWidget.tsx`
- **Purpose**: Last 10 org activity events with actor name, action description, and timestamp.

### 7.6 `RecentMeetingsWidget`
- **Path**: `features/dashboard/components/RecentMeetingsWidget.tsx`
- **Purpose**: Recent meeting sessions with status badges (RECORDING, PROCESSING, PROPOSALS_READY, COMPLETED).

### 7.7 `PendingProposalsWidget`
- **Path**: `features/dashboard/components/PendingProposalsWidget.tsx`
- **Purpose**: Displays count of pending AI task proposals awaiting manager review. Links to proposal queue.

### 7.8 `SmartSuggestionsWidget`
- **Path**: `features/dashboard/components/SmartSuggestionsWidget.tsx`
- **Purpose**: AI-powered workspace recommendations based on task and meeting data.

### 7.9 `QuickActionsWidget`
- **Path**: `features/dashboard/components/QuickActionsWidget.tsx`
- **Purpose**: Shortcut action buttons for common Manager/Admin tasks (new board, invite member, start meeting).

### 7.10 `FocusTasksWidget`
- **Path**: `features/dashboard/components/FocusTasksWidget.tsx`
- **Purpose**: Highlights high-priority or overdue tasks that need immediate attention.

---

## 8. Admin Feature (`src/features/admin/`)

> [!IMPORTANT]
> All admin components are gated to **Superadmin** role only via `<RequireRole allowedRoles={['SUPER_ADMIN']}>`.

### 8.1 `AdminLayout`
- **Path**: `features/admin/AdminLayout.tsx`
- **Purpose**: Layout shell for the admin panel. Renders admin navigation tabs.

### 8.2 `AdminDashboard`
- **Path**: `features/admin/AdminDashboard.tsx`
- **Purpose**: Admin panel home with navigation overview.

### 8.3 `UsersManagement`
- **Path**: `features/admin/UsersManagement.tsx`
- **Purpose**: Full user management table — list all org users, create new users directly, update roles (`MEMBER`/`MANAGER`/`SUPER_ADMIN`), and delete users.

### 8.4 `BoardPermissions`
- **Path**: `features/admin/BoardPermissions.tsx`
- **Purpose**: Assign/remove board members, manage board-level access per user.

---

## 9. Notification Components (`src/features/notifications/`)

### 9.1 `NotificationBell`
- **Path**: `features/notifications/NotificationBell.tsx`
- **Purpose**: Header bell icon with live unread badge count. Clicking toggles `NotificationPanel`.

### 9.2 `NotificationPanel`
- **Path**: `features/notifications/NotificationPanel.tsx`
- **Purpose**: Slide-in notification list panel. Displays all notifications, mark-all-read action. Reads from `notificationStore`.

### 9.3 `NotificationItem`
- **Path**: `features/notifications/NotificationItem.tsx`
- **Purpose**: Single notification entry. Resolves deep-link destination from notification payload (navigates to task modal, board view, or proposal queue).

---

## 10. Settings Feature (`src/features/settings/`)

### 10.1 `MyAccount`
- **Path**: `features/settings/MyAccount.tsx`
- **Purpose**: Edit profile (first name, last name, avatar). Calls `PATCH /api/v1/users/me`.

### 10.2 `Security`
- **Path**: `features/settings/Security.tsx`
- **Purpose**: Active multi-device session list with device info (browser, OS, IP, last active), one-click revocation of other sessions (`DELETE /auth/sessions/other`), and security event audit log (`GET /auth/security-events`). Also manages password change flow.

### 10.3 `Appearance`
- **Path**: `features/settings/Appearance.tsx`
- **Purpose**: Theme preferences (dark/light/system), UI density, and layout toggle settings.

### 10.4 `NotificationSettings`
- **Path**: `features/settings/NotificationSettings.tsx`
- **Purpose**: Configure per-channel notification preferences — in-app alerts, email digests, etc.

### 10.5 `Organization`
- **Path**: `features/settings/Organization.tsx`
- **Purpose**: Organization profile editing (name, branding). Full invitation management section — send new invitations and **revoke pending** ones (`DELETE /invitations/{id}`).

---

## 11. Auth Feature (`src/features/auth/`)

| Component | Path | Description |
|---|---|---|
| `LandingPage` | `features/auth/LandingPage.tsx` | Public marketing landing page with login/signup CTAs. |
| `Login` | `features/auth/Login.tsx` | Login form with email/password fields. On success, sets cookies and redirects to `/dashboard`. |
| `Signup` | `features/auth/Signup.tsx` | Organization registration form. Creates org + Superadmin account. |
| `AcceptInvitation` | `features/auth/AcceptInvitation.tsx` | Invitation acceptance page — validates token, collects name/password, creates account. |

---

## 12. Meeting Feature (`src/features/meeting/`)

Meeting UI components expose joining controls and active session status indicators. (See `05_MEETING_PIPELINE.md` for full pipeline details.)

---

## 13. My Work Feature (`src/features/my-work/`)

### 13.1 `MyWorkPage`
- **Path**: `features/my-work/MyWorkPage.tsx`
- **Purpose**: Aggregates tasks assigned to the current user across all boards. Supports `due` filter (all/today/week/overdue), `sort` (due/priority/created), and pagination.

---

## 14. Project Settings Feature (`src/features/projects/`)

### 14.1 `ProjectSettingsPage`
- **Path**: `features/projects/ProjectSettingsPage.tsx`
- **Purpose**: Board-level settings page — edit board name, description, project key, icon, color, cover gradient. Archived status toggle. Gated to Manager/Admin roles.

### 14.2 `ProjectSettingsLayout`
- **Path**: `features/projects/ProjectSettingsLayout.tsx`
- **Purpose**: Layout wrapper with tabs for General, Members, and Danger Zone board settings sections.

---

## 15. Timesheets Feature (`src/features/timesheets/`)

### 15.1 Member Timesheet Components (`src/features/timesheets/member/`)
- **`MyTimesheetsPage`** (`member/MyTimesheetsPage.tsx`): Main user timesheet workspace with week navigation bar, recent week tabs, rejection warning banner, and `+ Log Effort` button.
- **`TimesheetWeekView`** (`member/TimesheetWeekView.tsx`): Core weekly time logging grid. Renders daily column headers, project/task row groups, auto-save state indicators, and summary totals.
- **`TimesheetSummaryBar`** (`member/TimesheetSummaryBar.tsx`): Bottom sticky status bar displaying status badge, total hours, policy compliance check, and action buttons (`Submit for Approval`, `Recall`).
- **`TimeEntryRow`** (`member/TimeEntryRow.tsx`): Renders a single row of 7 daily time input cells for a specific task/general work item.

### 15.2 Member Modals (`src/features/timesheets/member/modals/`)
- **`AddBoardModal`**: Modal dialog for selecting an accessible project board to add to the timesheet.
- **`AddEntryModal`**: Modal for selecting work item type (task/general/leave/meeting) and specific task.
- **`EditEntryModal`**: Modal for editing specific entry date, hours, work item type, and description.
- **`LogEffortModal`**: Modal triggered by `+ Log Effort` button to log hours against any date and board/task.
- **`SubmitTimesheetModal`**: Submission dialog with optional member note and approver selection dropdown.
- **`RecallTimesheetModal`**: Confirmation modal to recall a submitted timesheet with mandatory reason input.

### 15.3 Approvals Feature Components (`src/features/timesheets/approvals/`)
- **`ApprovalQueuePage`** (`approvals/ApprovalQueuePage.tsx`): Manager/Superadmin approval workspace. Filterable table of submitted timesheets with status, days pending, overdue status, and review actions.
- **`ApprovalQueueSummaryCards`** (`approvals/ApprovalQueueSummaryCards.tsx`): Summary metrics cards (pending count, approved this week, rejected this week, avg hours approved).
- **`TimesheetReviewModal`** (`approvals/TimesheetReviewModal.tsx`): Deep review modal allowing managers to inspect all entries, daily totals, audit history, and execute `Approve` or `Reject` actions (with mandatory feedback comment).

### 15.4 Admin & Policy Components (`src/features/timesheets/admin/`)
- **`TimesheetAdminPage`** (`admin/TimesheetAdminPage.tsx`): Organization-wide timesheet configuration page (Superadmin-gated). Tabbed interface for Overview, Policy, Approvers, and Reports.
- **`TimesheetPolicyForm`** (`admin/TimesheetPolicyForm.tsx`): Form for configuring week start day, standard hours/day, max hours/day, overtime policy, deadline days, future entry rules, task link requirements, and recall toggles.
- **`ApproverAssignmentManager`** (`admin/ApproverAssignmentManager.tsx`): Interface for managing designated organization approvers.

### 15.5 Shared Helpers (`src/features/timesheets/shared/`)
- **`TimesheetErrorBanner`** (`shared/TimesheetErrorBanner.tsx`): Standardized error display banner mapping database error codes (`OVERTIME_BLOCKED`, `TASK_NOT_ASSIGNED`, `TASK_LINK_REQUIRED`, etc.) to user-friendly alert banners.
- **`TaskSearchSelector`** (`shared/TaskSearchSelector.tsx`): Auto-completing task search dropdown component for linking time entries directly to assigned Kanban tasks.

