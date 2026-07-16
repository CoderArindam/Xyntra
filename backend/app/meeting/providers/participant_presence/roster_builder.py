from datetime import datetime, timezone
from typing import Dict

from app.meeting.artifacts.speaker import (
    ParticipantPresenceTimeline,
    ParticipantRoster,
    MeetingParticipant,
    ParticipantJoined,
    ParticipantLeft,
    ParticipantRenamed,
    HostTransferred,
    ParticipantRejoined
)
from app.meeting.config import meeting_config

class ParticipantRosterBuilder:
    def build(self, timeline: ParticipantPresenceTimeline) -> ParticipantRoster:
        # Load snapshot as base, if available
        participants_map: Dict[str, MeetingParticipant] = {
            p.participant_id: p.model_copy() for p in timeline.current_snapshot
        }
        join_counter = len(participants_map)

        # Sort events by sequence number to ensure correct chronological replay
        sorted_events = sorted(timeline.events, key=lambda e: e.sequence_number)

        for event in sorted_events:
            pid = event.participant_id
            
            if isinstance(event, (ParticipantJoined, ParticipantRejoined)):
                if pid not in participants_map:
                    join_counter += 1
                    participants_map[pid] = MeetingParticipant(
                        participant_id=pid,
                        display_name=event.display_name,
                        join_time=event.timestamp,
                        join_order=join_counter,
                        is_bot=event.display_name.lower().strip() in (meeting_config.BOT_NAME.lower().strip(), "kai bot")
                    )
                
                p = participants_map[pid]
                if not p.first_seen:
                    p.first_seen = event.timestamp
                p.last_seen = event.timestamp
                if event.event_id not in p.join_events:
                    p.join_events.append(event.event_id)
                p.leave_time = None
                
            elif isinstance(event, ParticipantLeft):
                if pid in participants_map:
                    p = participants_map[pid]
                    p.last_seen = event.timestamp
                    if event.event_id not in p.leave_events:
                        p.leave_events.append(event.event_id)
                    p.leave_time = event.timestamp
                    
            elif isinstance(event, ParticipantRenamed):
                if pid in participants_map:
                    p = participants_map[pid]
                    p.display_name = event.new_display_name
                    p.last_seen = event.timestamp
                    
            elif isinstance(event, HostTransferred):
                if pid in participants_map:
                    participants_map[pid].is_host = False
                new_host_id = event.new_host_id
                if new_host_id in participants_map:
                    participants_map[new_host_id].is_host = True

        return ParticipantRoster(
            meeting_id=timeline.meeting_id,
            parent_presence_timeline_id=timeline.id if hasattr(timeline, "id") else None,
            source="google_meet",
            participants=list(participants_map.values()),
            captured_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            processing_version=timeline.processing_version
        )
