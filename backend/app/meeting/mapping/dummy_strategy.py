import time
from datetime import datetime, timezone
from typing import Optional

from app.meeting.artifacts.speaker import (
    ParticipantRoster,
    SpeakerMapping,
    SpeakerMappingEntry,
    SpeakerTimeline,
)
from app.meeting.config import meeting_config
from .strategy import SpeakerMappingStrategy


class DummyMappingStrategy(SpeakerMappingStrategy):
    """Development strategy: maps speakers sequentially based on roster discovery order."""

    @property
    def strategy_name(self) -> str:
        return "dummy"

    async def build_mapping(
        self,
        timeline: SpeakerTimeline,
        roster: Optional[ParticipantRoster],
    ) -> SpeakerMapping:
        start_dt = datetime.now(timezone.utc)
        t0 = time.monotonic()

        # Collect unique speaker labels in order of appearance
        speaker_labels = []
        seen = set()
        for turn in timeline.turns:
            if turn.speaker_label not in seen:
                seen.add(turn.speaker_label)
                speaker_labels.append(turn.speaker_label)

        participants = roster.participants if roster else []
        entries = []
        resolved = 0
        unresolved = 0

        # Map sequentially
        for i, label in enumerate(speaker_labels):
            if i < len(participants):
                p = participants[i]
                entries.append(
                    SpeakerMappingEntry(
                        speaker_label=label,
                        participant_id=p.participant_id,
                        participant_name=p.display_name,
                        mapping_confidence=1.0,
                        mapping_source=self.strategy_name,
                    )
                )
                resolved += 1
            else:
                entries.append(
                    SpeakerMappingEntry(
                        speaker_label=label,
                        participant_id=None,
                        participant_name=None,
                        mapping_confidence=0.0,
                        mapping_source=self.strategy_name,
                    )
                )
                unresolved += 1

        end_dt = datetime.now(timezone.utc)
        duration_ms = int((time.monotonic() - t0) * 1000)

        return SpeakerMapping(
            meeting_id=timeline.meeting_id,
            parent_speaker_timeline_id=timeline.id,
            parent_participant_roster_id=roster.id if roster else None,
            mapping_strategy=self.strategy_name,
            entries=entries,
            resolved_count=resolved,
            unresolved_count=unresolved,
            participant_count=len(participants),
            speaker_count=len(speaker_labels),
            mapping_started_at=start_dt.isoformat(),
            mapping_completed_at=end_dt.isoformat(),
            mapping_duration_ms=duration_ms,
            processing_version=meeting_config.MAPPING_PROCESSING_VERSION,
        )
