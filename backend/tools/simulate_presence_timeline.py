"""Developer tool to generate a realistic presence timeline for testing."""

import json
import uuid
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.meeting.artifacts.speaker import (
    ParticipantPresenceTimeline,
    ParticipantJoined,
    ParticipantLeft,
    ParticipantRenamed,
    HostTransferred,
    ParticipantRejoined,
    MeetingParticipant
)


def generate_timeline(meeting_id: str = "test-meeting") -> ParticipantPresenceTimeline:
    now = datetime.now(timezone.utc)
    t_start = now - timedelta(hours=1)
    
    events = []
    seq = 0
    
    def add_event(evt):
        nonlocal seq
        seq += 1
        evt.sequence_number = seq
        events.append(evt)

    # 1. Host joins
    t = t_start + timedelta(seconds=10)
    add_event(ParticipantJoined(
        event_id=str(uuid.uuid4()),
        sequence_number=0, # filled by add_event
        timestamp=t.isoformat(),
        source="MOCK",
        participant_id="host-123",
        display_name="Arindam"
    ))
    
    # Host gets transferred (maybe they created it, so they are made host)
    t = t + timedelta(seconds=2)
    add_event(HostTransferred(
        event_id=str(uuid.uuid4()),
        sequence_number=0,
        timestamp=t.isoformat(),
        source="MOCK",
        participant_id="system",
        new_host_id="host-123"
    ))

    # 2. Duplicate display names
    t = t + timedelta(minutes=5)
    add_event(ParticipantJoined(
        event_id=str(uuid.uuid4()),
        sequence_number=0,
        timestamp=t.isoformat(),
        source="MOCK",
        participant_id="user-john-1",
        display_name="John"
    ))
    
    t = t + timedelta(seconds=15)
    add_event(ParticipantJoined(
        event_id=str(uuid.uuid4()),
        sequence_number=0,
        timestamp=t.isoformat(),
        source="MOCK",
        participant_id="user-john-2",
        display_name="John"
    ))

    # 3. Rename
    t = t + timedelta(minutes=2)
    add_event(ParticipantRenamed(
        event_id=str(uuid.uuid4()),
        sequence_number=0,
        timestamp=t.isoformat(),
        source="MOCK",
        participant_id="host-123",
        new_display_name="Arindam Mukherjee"
    ))
    
    # 4. Disconnect and rejoin
    t = t + timedelta(minutes=10)
    add_event(ParticipantJoined(
        event_id=str(uuid.uuid4()),
        sequence_number=0,
        timestamp=t.isoformat(),
        source="MOCK",
        participant_id="user-samina",
        display_name="Samina"
    ))
    
    t = t + timedelta(minutes=20)
    add_event(ParticipantLeft(
        event_id=str(uuid.uuid4()),
        sequence_number=0,
        timestamp=t.isoformat(),
        source="MOCK",
        participant_id="user-samina",
    ))
    
    t = t + timedelta(minutes=2)
    add_event(ParticipantRejoined(
        event_id=str(uuid.uuid4()),
        sequence_number=0,
        timestamp=t.isoformat(),
        source="MOCK",
        participant_id="user-samina",
        display_name="Samina"
    ))

    # 5. Late Bot Admission
    t = t + timedelta(minutes=5)
    add_event(ParticipantJoined(
        event_id=str(uuid.uuid4()),
        sequence_number=0,
        timestamp=t.isoformat(),
        source="MOCK",
        participant_id="bot-999",
        display_name="KAIO Bot"
    ))
    
    return ParticipantPresenceTimeline(
        meeting_id=meeting_id,
        meeting_started_at=t_start.isoformat(),
        recording_started_at=(t_start + timedelta(minutes=30)).isoformat(), # audio started later
        timeline_started_at=t_start.isoformat(),
        events=events,
        current_snapshot=[], # A real collector updates this live
        processing_version="1.0.0"
    )

if __name__ == "__main__":
    timeline = generate_timeline()
    out_dir = Path("storage/meeting/recordings/test-meeting")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "participant_presence_timeline.json"
    out_path.write_text(timeline.model_dump_json(indent=2), encoding="utf-8")
    print(f"Generated {out_path}")
