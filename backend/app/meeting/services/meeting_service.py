"""MeetingService — top-level orchestration for the meeting module.

Responsibilities:
- Accept join / leave requests
- Fire async browser-join flows without blocking HTTP
- Coordinate: BrowserController -> Provider -> HealthMonitor -> ObserverSupervisor
- Bridge EventBus -> MeetingSession (service is the only writer to session state)
- Centralise all debug capture on failure
- Own a MeetingRuntime per session for deterministic cleanup

Dependency rules:
- Depends ONLY on meeting-internal components
- Never imports app.ai, app.services, app.auth, app.database, etc.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from app.meeting.bot.browser.controller import BrowserController
from app.meeting.bot.browser.profile_manager import ProfileManager
from app.meeting.bot.session.manager import MeetingSessionManager
from app.meeting.bot.session.monitor import HealthMonitor
from app.meeting.config import meeting_config
from app.meeting.exceptions import BrowserLaunchError, MeetingError
from app.meeting.intelligence.clock import MeetingClock
from app.meeting.intelligence.context import MeetingContext
from app.meeting.intelligence.event_bus import EventBus
from app.meeting.intelligence.lifecycle import MeetingLifecycle
from app.meeting.intelligence.models import (
    EventType,
    MeetingEvent,
    MeetingState,
    Participant,
    SpeakerSlot,
)
from app.meeting.intelligence.supervisor import ObserverSupervisor
from app.meeting.logger import get_logger
from app.meeting.models.session import JoinState, MeetingSession, SessionStatus, TERMINAL_STATUSES
from app.meeting.providers import get_provider
from app.meeting.utils.debug import DebugCapture
from app.meeting.utils.playwright_errors import is_playwright_fatal, page_is_usable
from app.meeting.utils.retry import with_retry

log = get_logger("service")


# ------------------------------------------------------------------ #
# Single-Owner Runtime Model                                           #
# ------------------------------------------------------------------ #

class RuntimeState(str, Enum):
    """Internal lifecycle of a MeetingRuntime."""
    STARTING = "starting"
    RUNNING = "running"
    LEAVING = "leaving"
    CLEANING_UP = "cleaning_up"
    CLOSED = "closed"


@dataclass
class MeetingRuntime:
    """The single-owner container for all resources of a session.
    
    Guarantees cleanup is executed exactly once via the join task.
    """
    session_id: str
    
    state: RuntimeState = RuntimeState.STARTING
    shutdown_reason: str | None = None
    _cleanup_event: asyncio.Event = field(default_factory=asyncio.Event)
    _cleanup_finished: asyncio.Event = field(default_factory=asyncio.Event)

    # Core Playwright
    controller: BrowserController | None = None
    profile_path: Path | None = None

    # Intelligence (populated after join)
    context: MeetingContext | None = None
    supervisor: ObserverSupervisor | None = None
    event_bus: EventBus | None = None
    lifecycle: MeetingLifecycle | None = None

    # Scalable task registry (join_flow, health_monitor, observers, transcription, etc.)
    background_tasks: dict[str, asyncio.Task] = field(default_factory=dict)
    
    # Specific timer task for empty meeting detection
    empty_timer_task: asyncio.Task | None = None
    
    def request_shutdown(self, reason: str) -> None:
        """Signal the join flow owner to begin teardown."""
        import inspect
        caller = inspect.currentframe().f_back
        caller_name = f"{caller.f_globals.get('__name__', 'unknown')}:{caller.f_code.co_name}" if caller else "unknown"
        log.info("cleanup_requested.set", reason=reason, caller=caller_name)
        if self.state in (RuntimeState.CLEANING_UP, RuntimeState.CLOSED):
            return
        self.shutdown_reason = reason
        self._cleanup_event.set()

    async def wait_for_shutdown(self) -> None:
        """Block until a shutdown is requested."""
        await self._cleanup_event.wait()

    async def wait_for_cleanup(self) -> None:
        """Block until the cleanup sequence is completely finished."""
        await self._cleanup_finished.wait()


# ------------------------------------------------------------------ #
# MeetingService                                                       #
# ------------------------------------------------------------------ #

class MeetingService:
    """High-level orchestrator — the only entry point for the meeting API."""

    def __init__(self) -> None:
        self._session_manager = MeetingSessionManager()
        self._monitor = HealthMonitor(self._session_manager)
        self._debug = DebugCapture(meeting_config.DEBUG_DIR)
        self._profile_manager = ProfileManager(meeting_config.PROFILE_ROOT)

        self._runtimes: dict[str, MeetingRuntime] = {}

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def join_meeting(self, meeting_url: str) -> MeetingSession:
        """Create a session and fire the join flow asynchronously."""
        session = self._session_manager.create(meeting_url)

        # Emit structured dump of every registered MeetingRuntime
        detailed_registry_dump = {}
        for sid, rt in self._runtimes.items():
            join_task = rt.background_tasks.get("join_flow")
            detailed_registry_dump[sid] = {
                "session_id": sid,
                "state": rt.state.value,
                "profile_name": rt.profile_path.name if rt.profile_path else None,
                "cleanup_requested": rt._cleanup_event.is_set(),
                "cleanup_completed": rt._cleanup_finished.is_set(),
                "join_task_is_none": join_task is None,
                "join_task_done": join_task.done() if join_task else None,
                "join_task_cancelled": join_task.cancelled() if join_task and join_task.done() else None,
                "join_task_exception": str(join_task.exception()) if join_task and join_task.done() and not join_task.cancelled() and not isinstance(join_task.exception(), asyncio.CancelledError) else None,
                "controller_exists": rt.controller is not None,
                "page_is_closed": rt.controller.get_page().is_closed() if rt.controller and hasattr(rt.controller, "get_page") and rt.controller.get_page() else None,
            }
        log.warning("diagnostic.registry_dump", dump=detailed_registry_dump)

        task = asyncio.create_task(
            self._run_join_flow(session.session_id, meeting_url),
            name=f"meeting-join-{session.session_id[:8]}",
        )

        log.info(
            "meeting.join.start — async task fired",
            session_id=session.session_id,
            url=meeting_url,
        )
        return session

    async def leave_meeting(self, session_id: str) -> MeetingSession | None:
        """Gracefully leave a meeting by signaling the runtime to shut down."""
        session = self._session_manager.get(session_id)
        if not session:
            return None

        self._session_manager.update_state(session_id, SessionStatus.LEAVING)
        
        runtime = self._runtimes.get(session_id)
        if runtime:
            if runtime.state == RuntimeState.RUNNING:
                runtime.state = RuntimeState.LEAVING
                log.info("runtime.leaving", session_id=session_id, runtime_state=runtime.state.value, profile_name=runtime.profile_path.name if runtime.profile_path else "unknown")
            runtime.request_shutdown("api_leave_requested")
            await runtime.wait_for_cleanup()

        return self._session_manager.get(session_id)

    def get_session(self, session_id: str) -> MeetingSession | None:
        return self._session_manager.get(session_id)

    def get_active_sessions(self) -> list[MeetingSession]:
        return self._session_manager.get_active()

    def cleanup_finished(self) -> int:
        return self._session_manager.cleanup()

    # ------------------------------------------------------------------ #
    # Shutdown — called by FastAPI lifespan on exit                        #
    # ------------------------------------------------------------------ #

    async def shutdown_all(self) -> None:
        """Signal all runtimes to shutdown and await their clean exit."""
        if not self._runtimes:
            log.info("shutdown.no_active_sessions")
            return

        log.info("shutdown.starting", active_sessions=len(self._runtimes))

        tasks_to_await = []
        for session_id, runtime in list(self._runtimes.items()):
            if runtime.state == RuntimeState.RUNNING:
                runtime.state = RuntimeState.LEAVING
                log.info("runtime.leaving", session_id=session_id, runtime_state=runtime.state.value, profile_name=runtime.profile_path.name if runtime.profile_path else "unknown")
            runtime.request_shutdown("server_shutdown")
            tasks_to_await.append(runtime.wait_for_cleanup())

        if tasks_to_await:
            await asyncio.gather(*tasks_to_await, return_exceptions=True)

        self._monitor.stop_all()
        log.info("shutdown.completed")

    # ------------------------------------------------------------------ #
    # Intelligence data accessors (used by API router)                     #
    # ------------------------------------------------------------------ #

    def get_participants(self, session_id: str) -> list[Participant]:
        runtime = self._runtimes.get(session_id)
        if not runtime or not runtime.supervisor:
            return []
        return runtime.supervisor.participant_tracker.get_participants()

    def get_timeline(self, session_id: str) -> list[MeetingEvent]:
        runtime = self._runtimes.get(session_id)
        if not runtime or not runtime.event_bus:
            return []
        return runtime.event_bus.get_history()

    def get_observer_health(self, session_id: str) -> dict[str, Any]:
        runtime = self._runtimes.get(session_id)
        if not runtime or not runtime.supervisor:
            return {}
        return runtime.supervisor.get_health()

    # ------------------------------------------------------------------ #
    # Internal — async join flow (SINGLE OWNER)                            #
    # ------------------------------------------------------------------ #

    async def _run_join_flow(self, session_id: str, meeting_url: str) -> None:
        """Full join sequence — the SINGLE OWNER of the session lifecycle."""
        runtime = MeetingRuntime(session_id=session_id)
        self._runtimes[session_id] = runtime

        # Track this join task itself
        current_task = asyncio.current_task()
        if current_task:
            runtime.background_tasks["join_flow"] = current_task

        controller = BrowserController()
        runtime.controller = controller
        
        profile_name = f"runtime_{session_id}"
        profile_path = self._profile_manager.get_profile_path(profile_name)
        runtime.profile_path = profile_path

        log.info("meeting.runtime.created", session_id=session_id)
        log.info("meeting.runtime.isolated", session_id=session_id, profile_path=str(profile_path))
        log.info("meeting.profile.created", session_id=session_id, profile_path=str(profile_path))
        log.info("meeting.runtime.started", session_id=session_id, runtime_state=runtime.state.value)
        log.info("runtime.starting", session_id=session_id, runtime_state=runtime.state.value, profile_name=profile_name)

        try:
            # ── Step 1: Browser launch ──────────────────────────── #
            self._session_manager.update_state(session_id, SessionStatus.AUTHENTICATING)

            # Clone the default authenticated profile to avoid CAPTCHA / 2FA issues on fresh browsers
            self._profile_manager.clone_profile("default", profile_name)
            self._profile_manager.lock(profile_path, session_id, profile_name)

            await with_retry(
                lambda: controller.launch_persistent(
                    str(profile_path),
                    headless=meeting_config.HEADLESS,
                    page_timeout=meeting_config.PAGE_TIMEOUT,
                ),
                max_attempts=meeting_config.RETRY_COUNT,
                base_delay=meeting_config.RETRY_BASE_DELAY,
                max_delay=meeting_config.RETRY_MAX_DELAY,
                retryable_exceptions=(BrowserLaunchError,),
                logger=log,
                session_id=session_id,
            )

            page = await controller.new_page()
            self._session_manager.attach_browser(session_id, controller, page)

            # ── Step 2: Resolve provider + authenticate ─────────────── #
            provider = get_provider(meeting_url)
            await provider.ensure_authenticated(page)

            # ── Step 3: Navigate to meeting ─────────────────────────── #
            self._session_manager.update_state(session_id, SessionStatus.OPENING_MEET)
            self._session_manager.update_state(session_id, SessionStatus.JOINING)

            join_state = await provider.join(page, meeting_url, meeting_config.BOT_NAME)
            self._session_manager.update_join_state(session_id, join_state)

            session = self._session_manager.get(session_id)
            if session:
                session.current_url = page.url

            # ── Step 4: Evaluate outcome and wait for shutdown ──────── #
            if join_state in (JoinState.IN_MEETING, JoinState.WAITING_FOR_ADMISSION):
                new_status = (
                    SessionStatus.IN_MEETING
                    if join_state == JoinState.IN_MEETING
                    else SessionStatus.WAITING_LOBBY
                )
                self._session_manager.update_state(session_id, new_status)
                await self._start_intelligence(session_id, page, runtime)
                
                monitor_task = self._monitor.start(
                    session_id, controller, page,
                    supervisor=runtime.supervisor,
                    shutdown_callback=lambda sid, reason: runtime.request_shutdown(reason),
                    shutdown_requested=lambda: runtime._cleanup_event.is_set(),
                )
                runtime.background_tasks["health_monitor"] = monitor_task
                
                log.info("meeting.join.success", session_id=session_id, join_state=join_state.value)
                
                # Yield control to the runtime. Wait until something requests shutdown.
                runtime.state = RuntimeState.RUNNING
                log.info("runtime.running", session_id=session_id, runtime_state=runtime.state.value, profile_name=profile_name)
                log.info("join_flow.waiting_for_cleanup")
                await runtime.wait_for_shutdown()
                log.info("join_flow.cleanup_signal_received")
                return

            elif join_state == JoinState.UNKNOWN_ERROR:
                log.warning("meeting.join.unknown_state — deferring to HealthMonitor", session_id=session_id)
                self._session_manager.update_state(session_id, SessionStatus.IN_MEETING)
                await self._start_intelligence(session_id, page, runtime)
                
                monitor_task = self._monitor.start(
                    session_id, controller, page,
                    supervisor=runtime.supervisor,
                    shutdown_callback=lambda sid, reason: runtime.request_shutdown(reason),
                    shutdown_requested=lambda: runtime._cleanup_event.is_set(),
                )
                runtime.background_tasks["health_monitor"] = monitor_task
                
                # Defer to HealthMonitor. Wait until shutdown requested.
                runtime.state = RuntimeState.RUNNING
                log.info("runtime.running", session_id=session_id, runtime_state=runtime.state.value, profile_name=profile_name)
                log.info("join_flow.waiting_for_cleanup")
                await runtime.wait_for_shutdown()
                log.info("join_flow.cleanup_signal_received")
                return

            else:
                # Definitive error state — capture diagnostics then trigger cleanup via finally
                if meeting_config.SCREENSHOT_ON_FAILURE:
                    debug_dir = await self._debug.capture(page, session_id, "join_failed")
                    if session:
                        session.debug_dir = debug_dir

                self._session_manager.fail(
                    session_id,
                    f"Join returned unexpected state: {join_state.value}",
                    join_state.value.upper(),
                )
                runtime.request_shutdown("join_failed")

        except asyncio.CancelledError:
            log.info("join_flow.cancelled", session_id=session_id)
            runtime.request_shutdown("join_task_cancelled")

        except Exception as exc:
            log.error(
                "join_flow.crashed",
                session_id=session_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )

            page = controller.get_page() if controller else None
            if page_is_usable(page) and meeting_config.SCREENSHOT_ON_FAILURE:
                try:
                    debug_dir = await self._debug.capture(page, session_id, "exception")
                    session = self._session_manager.get(session_id)
                    if session:
                        session.debug_dir = debug_dir
                except Exception:
                    pass

            error_code = exc.code if isinstance(exc, MeetingError) else "UNKNOWN_ERROR"
            self._session_manager.fail(session_id, str(exc), error_code)
            runtime.request_shutdown(f"exception_{type(exc).__name__}")

        finally:
            try:
                # ONLY this block is allowed to execute cleanup.
                await self._cleanup_runtime(runtime)
            except Exception as exc:
                log.critical("join_flow.fatal_cleanup_error", session_id=session_id, error=str(exc))

    # ------------------------------------------------------------------ #
    # Deterministic Teardown                                               #
    # ------------------------------------------------------------------ #

    async def _cleanup_runtime(self, runtime: MeetingRuntime) -> None:
        """Deterministic, idempotent cleanup, executed ONLY by the join flow task."""
        log.info("meeting.runtime.cleanup_started", session_id=runtime.session_id, runtime_state=runtime.state.value)
        log.info("cleanup.started")
        if runtime.state in (RuntimeState.CLEANING_UP, RuntimeState.CLOSED):
            return
            
        import time
        start_time = time.time()
        
        profile_name = runtime.profile_path.name if runtime.profile_path else "unknown"
        log.info("cleanup.started", session_id=runtime.session_id, runtime_state=runtime.state.value, profile_name=profile_name, reason=runtime.shutdown_reason)
        
        # 1. Signal Shutdown
        t_stage = time.time()
        log.info("cleanup.signal_shutdown.start", session_id=runtime.session_id)
        runtime.state = RuntimeState.CLEANING_UP
        runtime.shutdown_reason = runtime.shutdown_reason or "cleanup"
        import inspect
        caller = inspect.currentframe().f_back
        caller_name = f"{caller.f_globals.get('__name__', 'unknown')}:{caller.f_code.co_name}" if caller else "unknown"
        log.info("cleanup_requested.set", reason=runtime.shutdown_reason, caller=caller_name)
        runtime._cleanup_event.set()
        session = self._session_manager.get(runtime.session_id)
        if session and session.status not in TERMINAL_STATUSES:
            try:
                self._session_manager.update_state(runtime.session_id, SessionStatus.CLEANING_UP)
            except Exception as exc:
                log.error("cleanup.update_state_error", session_id=runtime.session_id, error=str(exc))
        log.info("cleanup.signal_shutdown.complete", session_id=runtime.session_id, duration_ms=int((time.time() - t_stage) * 1000))

        # 2. Monitor Shutdown (cooperative exit)
        t_stage = time.time()
        log.info("cleanup.monitor_shutdown.start", session_id=runtime.session_id)
        monitor_task = runtime.background_tasks.pop("health_monitor", None)
        if monitor_task and not monitor_task.done():
            try:
                # Give it 2s to exit cooperatively now that shutdown_requested is true
                await asyncio.wait_for(asyncio.shield(monitor_task), timeout=2.0)
            except asyncio.TimeoutError:
                log.warning("cleanup.monitor_cooperative_exit_timeout", session_id=runtime.session_id)
                monitor_task.cancel()
                try:
                    await asyncio.wait_for(monitor_task, timeout=2.0)
                except Exception:
                    pass
            except Exception:
                pass
        log.info("cleanup.monitor_shutdown.complete", session_id=runtime.session_id, duration_ms=int((time.time() - t_stage) * 1000))

        # 3. Stop Observers
        t_stage = time.time()
        log.info("cleanup.observers_stop.start", session_id=runtime.session_id)
        try:
            if runtime.supervisor:
                await asyncio.wait_for(runtime.supervisor.stop_all(), timeout=5.0)
                if session:
                    session.intelligence_alive = False
        except asyncio.TimeoutError:
            log.warning("cleanup.observers_stop.timeout", session_id=runtime.session_id)
        except Exception as exc:
            log.warning("cleanup.observers_stop_error", session_id=runtime.session_id, error=str(exc))
        log.info("cleanup.observers_stop.complete", session_id=runtime.session_id, duration_ms=int((time.time() - t_stage) * 1000))

        # 4. Cancel Remaining Tasks
        t_stage = time.time()
        log.info("cleanup.cancel_tasks.start", session_id=runtime.session_id)
        try:
            current = asyncio.current_task()
            tasks_to_cancel = [
                t for name, t in runtime.background_tasks.items()
                if not t.done() and t is not current
            ]
            for t in tasks_to_cancel:
                t.cancel()
            if tasks_to_cancel:
                await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
        except Exception as exc:
            log.warning("cleanup.tasks_cancel_error", session_id=runtime.session_id, error=str(exc))
        log.info("cleanup.cancel_tasks.complete", session_id=runtime.session_id, duration_ms=int((time.time() - t_stage) * 1000))

        # 5. Leave Meeting
        t_stage = time.time()
        log.info("cleanup.leave_meeting.start", session_id=runtime.session_id)
        try:
            if runtime.controller:
                page = runtime.controller.get_page()
                if page_is_usable(page):
                    provider = get_provider(session.meeting_url if session else "")
                    await asyncio.wait_for(provider.leave(page), timeout=5.0)
        except asyncio.TimeoutError:
            log.warning("cleanup.leave_meeting.timeout", session_id=runtime.session_id)
        except Exception as exc:
            log.warning("cleanup.leave_failed", session_id=runtime.session_id, error=str(exc))
        log.info("cleanup.leave_meeting.complete", session_id=runtime.session_id, duration_ms=int((time.time() - t_stage) * 1000))

        # 6. Close Browser
        t_stage = time.time()
        log.info("cleanup.browser_close.start", session_id=runtime.session_id)
        try:
            if runtime.controller:
                await asyncio.wait_for(runtime.controller.close(), timeout=5.0)
                if runtime.controller.is_closed:
                    log.info("runtime.browser_closed", session_id=runtime.session_id, runtime_state=runtime.state.value, profile_name=profile_name)
        except asyncio.TimeoutError:
            log.warning("cleanup.browser_close.timeout", session_id=runtime.session_id)
        except Exception as exc:
            log.warning("cleanup.browser_close_error", session_id=runtime.session_id, error=str(exc))
        log.info("cleanup.browser_close.complete", session_id=runtime.session_id, duration_ms=int((time.time() - t_stage) * 1000))

        # 7. Unlock Profile
        t_stage = time.time()
        log.info("cleanup.profile_unlock.start", session_id=runtime.session_id)
        try:
            if runtime.profile_path:
                self._profile_manager.unlock(runtime.profile_path, runtime.session_id)
                log.info("runtime.profile_unlocked", session_id=runtime.session_id, runtime_state=runtime.state.value, profile_name=profile_name)
        except Exception as exc:
            log.warning("cleanup.profile_unlock_error", session_id=runtime.session_id, error=str(exc))
        log.info("cleanup.profile_unlock.complete", session_id=runtime.session_id, duration_ms=int((time.time() - t_stage) * 1000))

        # 8. Profile Deletion (Retry-Safe)
        t_stage = time.time()
        log.info("cleanup.profile_deletion.start", session_id=runtime.session_id)
        try:
            if runtime.profile_path:
                await self._profile_manager.remove_when_available(runtime.profile_path, runtime.session_id)
                log.info("meeting.profile.deleted", session_id=runtime.session_id, profile_path=str(runtime.profile_path))
        except Exception as exc:
            log.warning("cleanup.profile_deletion_error", session_id=runtime.session_id, error=str(exc))
        log.info("cleanup.profile_deletion.complete", session_id=runtime.session_id, duration_ms=int((time.time() - t_stage) * 1000))

        # 9. Remove Registry
        t_stage = time.time()
        log.info("cleanup.registry_remove.start", session_id=runtime.session_id)
        try:
            self._runtimes.pop(runtime.session_id, None)
        except Exception as exc:
            log.warning("cleanup.runtime_remove_error", session_id=runtime.session_id, error=str(exc))
        log.info("cleanup.registry_remove.complete", session_id=runtime.session_id, duration_ms=int((time.time() - t_stage) * 1000))

        # 10. Finished
        try:
            runtime.state = RuntimeState.CLOSED
            if session and session.status not in TERMINAL_STATUSES:
                self._session_manager.update_state(runtime.session_id, SessionStatus.FINISHED)
            log.info("runtime.closed", session_id=runtime.session_id, runtime_state=runtime.state.value, profile_name=profile_name)
        except Exception as exc:
            log.warning("cleanup.finalize_error", session_id=runtime.session_id, error=str(exc))
            
        runtime._cleanup_finished.set()
        log.info("meeting.runtime.cleanup_finished", session_id=runtime.session_id)
        log.info("meeting.runtime.destroyed", session_id=runtime.session_id)
        log.info("cleanup.finished", session_id=runtime.session_id, total_duration_ms=int((time.time() - start_time) * 1000))

    # ------------------------------------------------------------------ #
    # Intelligence orchestration                                           #
    # ------------------------------------------------------------------ #

    async def _start_intelligence(
        self, session_id: str, page: Any, runtime: MeetingRuntime
    ) -> None:
        """Create MeetingContext and start all intelligence observers."""
        event_bus = EventBus()
        clock = MeetingClock()
        lifecycle = MeetingLifecycle(session_id)
        supervisor = ObserverSupervisor()

        ctx = MeetingContext(
            session_id=session_id,
            page=page,
            config=meeting_config,
            event_bus=event_bus,
            clock=clock,
            bot_name=meeting_config.BOT_NAME,
        )

        runtime.context = ctx
        runtime.supervisor = supervisor
        runtime.event_bus = event_bus
        runtime.lifecycle = lifecycle

        # Subscribe to event bus before starting observers
        event_bus.subscribe(None, self._make_event_handler(session_id))

        observer_tasks = await supervisor.start_all(ctx)
        runtime.background_tasks.update(observer_tasks)

        session = self._session_manager.get(session_id)
        if session:
            session.intelligence_alive = True
            session.observer_health = supervisor.get_health()

        log.info("observers.started", session_id=session_id)

    def _make_event_handler(self, session_id: str):
        """Return a bound async handler for a given session."""
        async def _handler(event: MeetingEvent) -> None:
            await self._on_intelligence_event(session_id, event)
        return _handler

    async def _on_intelligence_event(self, session_id: str, event: MeetingEvent) -> None:
        """Bridge EventBus events -> MeetingSession state.

        This is the ONLY place that writes intelligence data to MeetingSession.
        Observers only read from session; they never write to it.
        """
        log.info("meeting_service.event_received", event=event.type.value)
        session = self._session_manager.get(session_id)
        runtime = self._runtimes.get(session_id)
        if not session or not runtime or not runtime.supervisor:
            return

        et = event.type

        if et in (EventType.PARTICIPANT_JOINED, EventType.PARTICIPANT_LEFT, EventType.PARTICIPANT_UPDATED):
            participants = runtime.supervisor.participant_tracker.get_participants()
            session.participants_detailed = participants
            session.participants = [
                p.display_name for p in participants if p.is_present
            ]
            present_count = sum(1 for p in participants if p.is_present)
            if runtime.lifecycle:
                runtime.lifecycle.update_participant_count(present_count)
                session.peak_participants = runtime.lifecycle.peak_participants
            session.participant_events.append(event)
            session.observer_health = runtime.supervisor.get_health()

            # Empty Meeting Detector
            tracker = runtime.supervisor.participant_tracker
            if tracker.is_only_bot_present():
                if runtime.empty_timer_task is None or runtime.empty_timer_task.done():
                    log.info("meeting.empty_detected", session_id=session_id)
                    runtime.empty_timer_task = asyncio.create_task(
                        self._empty_meeting_countdown(session_id, runtime),
                        name=f"empty-timer-{session_id[:8]}"
                    )
            else:
                if runtime.empty_timer_task and not runtime.empty_timer_task.done():
                    runtime.empty_timer_task.cancel()
                    runtime.empty_timer_task = None
                    log.info("meeting.empty_timer_cancelled", session_id=session_id)

        elif et == EventType.HOST_JOINED:
            participant_name = event.payload.get("participant", {}).get("display_name", "")
            if participant_name and runtime.lifecycle:
                runtime.lifecycle.record_host(participant_name)
                log.info(
                    "meeting.host_joined",
                    session_id=session_id,
                    host=participant_name,
                )

        elif et == EventType.SPEAKER_CHANGED:
            session.active_speaker = runtime.supervisor.speaker_detector.get_active_speaker()
            session.speaker_timeline = runtime.supervisor.speaker_detector.get_speaker_timeline()

        elif et in (
            EventType.MEETING_STATE_CHANGED,
            EventType.MEETING_STARTED,
            EventType.MEETING_ENDED,
            EventType.NETWORK_LOST,
        ):
            new_state = event.payload.get("new_state", "unknown")
            session.meeting_state = new_state

            if et == EventType.MEETING_STARTED:
                session.meeting_started_at = event.timestamp
                if runtime.lifecycle:
                    runtime.lifecycle.record_start(event.timestamp)
                log.info(
                    "meeting.started",
                    session_id=session_id,
                    elapsed=event.payload.get("elapsed_seconds"),
                )
            elif et == EventType.MEETING_ENDED:
                session.meeting_ended_at = event.timestamp
                if runtime.lifecycle:
                    runtime.lifecycle.record_end(event.timestamp)
                elapsed = event.payload.get("elapsed_seconds")
                if elapsed is not None:
                    session.meeting_duration = elapsed
                if new_state == "host_ended_meeting":
                    log.info("meeting.host_ended", session_id=session_id)

                log.info(
                    "meeting.ended",
                    session_id=session_id,
                    duration=session.meeting_duration,
                    meeting_state=new_state,
                )
                runtime.request_shutdown(f"meeting_ended_{new_state}")
            elif et == EventType.NETWORK_LOST:
                log.warning(
                    "meeting.network_lost",
                    session_id=session_id,
                    meeting_state=new_state,
                )

        elif et == EventType.OBSERVER_RESTARTED:
            session.observer_health = runtime.supervisor.get_health()
            log.info(
                "meeting.observer_restarted",
                session_id=session_id,
                observer=event.payload.get("observer"),
                restart_count=event.payload.get("restart_count"),
            )

    async def _empty_meeting_countdown(self, session_id: str, runtime: MeetingRuntime) -> None:
        """Countdown timer before leaving an empty meeting."""
        log.info("meeting.empty_timer_created", session_id=session_id)
        try:
            await asyncio.sleep(meeting_config.EMPTY_TIMEOUT_SECONDS)
            log.info("meeting.empty_timeout", session_id=session_id)
            log.info("meeting.auto_leave_requested", session_id=session_id)
            log.info("meeting.empty_timer_completed", session_id=session_id)
            runtime.request_shutdown("empty_meeting_timeout")
        except asyncio.CancelledError:
            pass
