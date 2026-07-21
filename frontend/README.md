# KAIO Frontend Web Application

The **KAIO Frontend** is an enterprise-grade single-page web application (SPA) built using **React 18**, **TypeScript**, **Vite**, and **Tailwind CSS**.

---

## 🚀 Key Features

1. **Interactive Kanban Boards**:
   - Dynamic column re-ordering, task creation, assignment, priority tagging, and detailed modal views.
   - Project settings modal gated by role access control (`isManagerOrAdmin`).

2. **Meeting Automation & AI Task Proposals**:
   - Single-click Playwright bot deployment to Google Meet sessions.
   - Real-time meeting status bar (`JOINING`, `RECORDING`, `PROCESSING`, `PROPOSALS_READY`).
   - Speaker-attributed transcript viewer with confidence metrics.
   - Interactive manager approval drawer for reviewing, editing, approving (`fn_approve_task_proposal`), and rejecting AI task proposals.

3. **Notification System**:
   - Header notification bell with real-time unread badge count.
   - In-place notification dropdown drawer with mark-all-read action.
   - Destination deep-linking resolver (links directly to tasks, comments, boards, or task proposals).

4. **Security & Session Management**:
   - Multi-device active session tab allowing users to inspect device name, OS, IP address, and last active time with session revocation.
   - Complete login activity history log displaying authentication and security audit events.

---

## 🛠️ Tech Stack & Dependencies

- **Core**: React 18, TypeScript, Vite
- **Styling**: Tailwind CSS, Lucide React Icons
- **State Management**: React Context (`AuthContext`, `BoardContext`, `MeetingContext`)
- **HTTP Client**: Axios with Bearer JWT interceptors and auto-refresh logic
- **Routing**: React Router DOM (v6+)

---

## 💻 Available Scripts

```bash
# Start Vite development server
npm run dev

# Typecheck and build production bundle
npm run build

# Preview production build locally
npm run preview
```

