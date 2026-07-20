"""MeetingSessionManager — state machine and in-memory session store.

CRITICAL: All session state transitions must go through update_state().
No component outside this module should mutate session.status directly.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.meeting.config import meeting_config
from app.meeting.logger import get_logger
from app.meeting.models.session import (
    ACTIVE_STATUSES,
    TERMINAL_STATUSES,
    JoinState,
    MeetingSession,
    SessionStatus,
)

if TYPE_CHECKING:
    from app.meeting.bot.browser.controller import BrowserController

log = get_logger("session.manager")

# Legal state transitions — prevents illegal jumps
_ALLOWED_TRANSITIONS: dict[SessionStatus, frozenset[SessionStatus]] = {
    SessionStatus.STARTING: frozenset({SessionStatus.AUTHENTICATING, SessionStatus.FAILED, SessionStatus.CLEANING_UP}),
    SessionStatus.AUTHENTICATING: frozenset({SessionStatus.OPENING_MEET, SessionStatus.FAILED, SessionStatus.CLEANING_UP}),
    SessionStatus.OPENING_MEET: frozenset({SessionStatus.JOINING, SessionStatus.FAILED, SessionStatus.CLEANING_UP}),
    SessionStatus.JOINING: frozenset({SessionStatus.IN_MEETING, SessionStatus.WAITING_LOBBY, SessionStatus.FAILED, SessionStatus.CLEANING_UP}),
    SessionStatus.WAITING_LOBBY: frozenset({SessionStatus.IN_MEETING, SessionStatus.FAILED, SessionStatus.LEAVING, SessionStatus.CLEANING_UP}),
    SessionStatus.IN_MEETING: frozenset({SessionStatus.LEAVING, SessionStatus.FAILED, SessionStatus.CLEANING_UP}),
    SessionStatus.LEAVING: frozenset({SessionStatus.FINISHED, SessionStatus.FAILED, SessionStatus.CLEANING_UP}),
    SessionStatus.CLEANING_UP: frozenset({SessionStatus.FINISHED, SessionStatus.FAILED}),
    SessionStatus.FINISHED: frozenset(),   # terminal
    SessionStatus.FAILED: frozenset(),     # terminal
}


class _SessionResources:
    """Holds per-session Playwright resources (opaque to callers)."""

    def __init__(self) -> None:
        self.controller: Any = None   # BrowserController
        self.page: Any = None         # Playwright Page


class MeetingSessionManager:
    """In-memory store and state machine for MeetingSession objects.

    Rules:
    - All status changes go through update_state().
    - Browser resources attach / detach via attach_browser / detach_browser.
    - Concurrency limit enforced on create().
    """

    def __init__(self) -> None:
        self._sessions: dict[str, MeetingSession] = {}
        self._resources: dict[str, _SessionResources] = {}
        log.debug("MeetingSessionManager initialized")

    # ------------------------------------------------------------------ #
    # CRUD                                                                 #
    # ------------------------------------------------------------------ #

    def create(
        self,
        meeting_url: str,
        session_id: str | None = None,
        org_id: int = 1,
        metadata: dict | None = None
    ) -> MeetingSession:
        active = [s for s in self._sessions.values() if s.status in ACTIVE_STATUSES]
        if len(active) >= meeting_config.MAX_CONCURRENT_SESSIONS:
            raise RuntimeError(
                f"Max concurrent sessions ({meeting_config.MAX_CONCURRENT_SESSIONS}) reached. "
                "Leave an existing session before starting a new one."
            )

        kwargs: dict[str, Any] = {"meeting_url": meeting_url, "org_id": org_id}
        if session_id:
            kwargs["session_id"] = session_id
        if metadata:
            kwargs["metadata"] = metadata

        session = MeetingSession(**kwargs)
        self._sessions[session.session_id] = session
        self._resources[session.session_id] = _SessionResources()
        log.info("Session created", session_id=session.session_id, url=meeting_url, org_id=org_id)
        return session

    def get(self, session_id: str) -> MeetingSession | None:
        return self._sessions.get(session_id)

    def get_by_meeting_id(self, meeting_id: str) -> MeetingSession | None:
        """Find a session by its Google Meet code (e.g. abc-defg-hij)."""
        for session in self._sessions.values():
            if session.meeting_url.endswith(meeting_id):
                return session
        return None

    def get_active(self) -> list[MeetingSession]:
        return [s for s in self._sessions.values() if s.status in ACTIVE_STATUSES]

    def cleanup(self) -> int:
        to_remove = [
            sid for sid, s in self._sessions.items()
            if s.status in TERMINAL_STATUSES
        ]
        for sid in to_remove:
            del self._sessions[sid]
            self._resources.pop(sid, None)
        if to_remove:
            log.info("Cleaned up %d terminated sessions", len(to_remove))
        return len(to_remove)

    # ------------------------------------------------------------------ #
    # State machine                                                        #
    # ------------------------------------------------------------------ #

    def update_state(self, session_id: str, new_status: SessionStatus) -> None:
        """Transition a session to a new status.

        Enforces allowed transitions and records timestamps for terminal states.
        """
        session = self._sessions.get(session_id)
        if not session:
            log.warning("update_state called for unknown session", session_id=session_id)
            return

        allowed = _ALLOWED_TRANSITIONS.get(session.status, frozenset())
        if new_status not in allowed:
            log.warning(
                "Illegal state transition ignored",
                session_id=session_id,
                current=session.status.value,
                attempted=new_status.value,
            )
            return

        old = session.status.value
        session.status = new_status

        if new_status == SessionStatus.IN_MEETING and session.started_at is None:
            session.started_at = datetime.now(timezone.utc)
        if new_status in TERMINAL_STATUSES:
            session.ended_at = datetime.now(timezone.utc)

        log.info(
            "Session state transition",
            session_id=session_id,
            from_state=old,
            to_state=new_status.value,
        )

    def fail(self, session_id: str, error: str, error_code: str = "UNKNOWN_ERROR") -> None:
        session = self._sessions.get(session_id)
        if not session:
            return
        session.error = error
        session.error_code = error_code
        session.browser_alive = False
        session.page_alive = False
        # Force to FAILED regardless of current state
        session.status = SessionStatus.FAILED
        session.ended_at = datetime.now(timezone.utc)
        log.error(
            "Session failed",
            session_id=session_id,
            error_code=error_code,
            error=error,
        )

    def update_join_state(self, session_id: str, join_state: JoinState) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.join_state = join_state

    # ------------------------------------------------------------------ #
    # Browser resource management                                          #
    # ------------------------------------------------------------------ #

    def attach_browser(
        self,
        session_id: str,
        controller: Any,  # BrowserController
        page: Any,
    ) -> None:
        resources = self._resources.get(session_id)
        if resources:
            resources.controller = controller
            resources.page = page
            session = self._sessions.get(session_id)
            if session:
                session.browser_alive = True
                session.page_alive = True

    def detach_browser(self, session_id: str) -> tuple[Any, Any]:
        """Remove and return (controller, page) for the session."""
        resources = self._resources.get(session_id)
        if not resources:
            return None, None
        controller, page = resources.controller, resources.page
        resources.controller = None
        resources.page = None
        session = self._sessions.get(session_id)
        if session:
            session.browser_alive = False
            session.page_alive = False
        return controller, page

    def get_browser_resources(self, session_id: str) -> tuple[Any, Any]:
        """Return (controller, page) without detaching."""
        resources = self._resources.get(session_id)
        if not resources:
            return None, None
        return resources.controller, resources.page
