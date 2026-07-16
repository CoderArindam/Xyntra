import asyncio
from datetime import datetime
from typing import Dict, Any, List

from app.meeting.artifacts.speaker import (
    ParticipantPresenceTimeline,
    AnyPresenceEvent,
    ParticipantJoined,
    ParticipantLeft,
    ParticipantRenamed,
    HostTransferred,
    ParticipantRejoined,
    MeetingParticipant
)
from app.meeting.contracts.participant_presence_provider import ParticipantPresenceProvider
from .recorder import EventRecorder


class ExternalPresenceProvider(ParticipantPresenceProvider):
    """
    Event receiver for externally generated presence events.
    Does not interact directly with meeting platforms. External clients
    (e.g., Chrome extension, Bot, API client) push events to this provider,
    which builds the internal timeline state.
    """

    def __init__(self, meeting_id: str, recording_started_at: str = None, recorder: EventRecorder = None):
        self.meeting_id = meeting_id
        self.recording_started_at = recording_started_at
        self.recorder = recorder
        
        self._timeline_started_at = datetime.utcnow().isoformat() + "Z"
        self._events: List[AnyPresenceEvent] = []
        self._current_snapshot: Dict[str, MeetingParticipant] = {}
        
        self._sequence_counter = 0
        self._lock = asyncio.Lock()
        self._is_collecting = False
        
        self._processed_event_ids: set[str] = set()
        self.last_heartbeat_at: datetime = None
        self.active_tabs: int = 0
        self.content_script_connected: bool = False

    async def start(self) -> None:
        self._is_collecting = True

    async def stop(self) -> None:
        self._is_collecting = False

    async def collect(self, meeting_id: str, **kwargs) -> ParticipantPresenceTimeline:
        async with self._lock:
            return ParticipantPresenceTimeline(
                meeting_id=self.meeting_id,
                meeting_started_at=self._timeline_started_at,
                recording_started_at=self.recording_started_at,
                timeline_started_at=self._timeline_started_at,
                events=list(self._events),
                current_snapshot=list(self._current_snapshot.values()),
                processing_version="1.0.0"
            )

    def get_current_snapshot(self) -> List[MeetingParticipant]:
        return list(self._current_snapshot.values())

    def _next_sequence(self) -> int:
        self._sequence_counter += 1
        return self._sequence_counter
        
    def _create_participant(self, participant_id: str, display_name: str) -> MeetingParticipant:
        from app.meeting.config import meeting_config
        return MeetingParticipant(
            participant_id=participant_id,
            display_name=display_name,
            join_time=datetime.utcnow().isoformat() + "Z",
            join_order=len(self._current_snapshot) + 1,
            is_bot=display_name.lower().strip() in (meeting_config.BOT_NAME.lower().strip(), "kai bot")
        )

    async def _persist_timeline(self):
        if self.recorder:
            timeline = await self.collect(self.meeting_id)
            await self.recorder.persist(timeline)

    async def handle_heartbeat(self, timestamp: str = None, active_tabs: int = 0, content_script_connected: bool = False) -> None:
        self.last_heartbeat_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00")) if timestamp else datetime.utcnow()
        self.active_tabs = active_tabs
        self.content_script_connected = content_script_connected

    async def handle_join(self, event_id: str, participant_id: str, display_name: str, source: str = "EXTERNAL", timestamp: str = None) -> None:
        if not self._is_collecting:
            return
            
        timestamp = timestamp or datetime.utcnow().isoformat() + "Z"
        
        async with self._lock:
            if event_id in self._processed_event_ids:
                return
            self._processed_event_ids.add(event_id)
            
            event = ParticipantJoined(
                event_id=event_id,
                sequence_number=self._next_sequence(),
                timestamp=timestamp,
                source=source,
                participant_id=participant_id,
                display_name=display_name
            )
            self._events.append(event)
            
            if participant_id not in self._current_snapshot:
                self._current_snapshot[participant_id] = self._create_participant(participant_id, display_name)
            
            p = self._current_snapshot[participant_id]
            if not p.first_seen:
                p.first_seen = timestamp
            p.last_seen = timestamp
            p.join_events.append(event_id)
            p.leave_time = None
        
        await self._persist_timeline()

    async def handle_leave(self, event_id: str, participant_id: str, source: str = "EXTERNAL", timestamp: str = None) -> None:
        if not self._is_collecting:
            return
            
        timestamp = timestamp or datetime.utcnow().isoformat() + "Z"
        
        async with self._lock:
            if event_id in self._processed_event_ids:
                return
            self._processed_event_ids.add(event_id)
            
            event = ParticipantLeft(
                event_id=event_id,
                sequence_number=self._next_sequence(),
                timestamp=timestamp,
                source=source,
                participant_id=participant_id
            )
            self._events.append(event)
            
            if participant_id in self._current_snapshot:
                p = self._current_snapshot[participant_id]
                p.last_seen = timestamp
                p.leave_events.append(event_id)
                p.leave_time = timestamp
                
        await self._persist_timeline()

    async def handle_rename(self, event_id: str, participant_id: str, new_display_name: str, source: str = "EXTERNAL", timestamp: str = None) -> None:
        if not self._is_collecting:
            return
            
        timestamp = timestamp or datetime.utcnow().isoformat() + "Z"
        
        async with self._lock:
            if event_id in self._processed_event_ids:
                return
            self._processed_event_ids.add(event_id)
            
            event = ParticipantRenamed(
                event_id=event_id,
                sequence_number=self._next_sequence(),
                timestamp=timestamp,
                source=source,
                participant_id=participant_id,
                new_display_name=new_display_name
            )
            self._events.append(event)
            
            if participant_id in self._current_snapshot:
                p = self._current_snapshot[participant_id]
                p.display_name = new_display_name
                p.last_seen = timestamp

        await self._persist_timeline()

    async def handle_host_transfer(self, event_id: str, old_host_id: str, new_host_id: str, source: str = "EXTERNAL", timestamp: str = None) -> None:
        if not self._is_collecting:
            return
            
        timestamp = timestamp or datetime.utcnow().isoformat() + "Z"
        
        async with self._lock:
            if event_id in self._processed_event_ids:
                return
            self._processed_event_ids.add(event_id)
            
            event = HostTransferred(
                event_id=event_id,
                sequence_number=self._next_sequence(),
                timestamp=timestamp,
                source=source,
                participant_id=old_host_id,  # Context participant
                new_host_id=new_host_id
            )
            self._events.append(event)
            
            if old_host_id in self._current_snapshot:
                self._current_snapshot[old_host_id].is_host = False
            if new_host_id in self._current_snapshot:
                self._current_snapshot[new_host_id].is_host = True

        await self._persist_timeline()
