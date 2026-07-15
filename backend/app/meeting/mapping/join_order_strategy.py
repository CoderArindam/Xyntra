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


class JoinOrderMappingStrategy(SpeakerMappingStrategy):
    """Production strategy: maps participants by correlating join order with first appearance."""

    @property
    def strategy_name(self) -> str:
        return "join_order"

    async def build_mapping(
        self,
        timeline: SpeakerTimeline,
        roster: Optional[ParticipantRoster],
    ) -> SpeakerMapping:
        start_dt = datetime.now(timezone.utc)
        t0 = time.monotonic()

        # Collect unique speaker labels in order of their first timestamp
        speaker_first_appearance = {}
        for turn in timeline.turns:
            if turn.speaker_label not in speaker_first_appearance:
                speaker_first_appearance[turn.speaker_label] = turn.start_time

        # Sort speakers by first appearance
        sorted_speakers = sorted(speaker_first_appearance.keys(), key=lambda lbl: speaker_first_appearance[lbl])

        participants = []
        if roster:
            # Sort participants by join_order (1-indexed, so 1 comes before 2)
            participants = sorted(roster.participants, key=lambda p: p.join_order)

        entries = []
        resolved = 0
        unresolved = 0

        # Map sequentially based on these sorted lists
        for i, label in enumerate(sorted_speakers):
            if i < len(participants):
                p = participants[i]
                entries.append(
                    SpeakerMappingEntry(
                        speaker_label=label,
                        participant_id=p.participant_id,
                        participant_name=p.display_name,
                        mapping_confidence=0.65,  # Heuristic confidence
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
            speaker_count=len(sorted_speakers),
            mapping_started_at=start_dt.isoformat(),
            mapping_completed_at=end_dt.isoformat(),
            mapping_duration_ms=duration_ms,
            processing_version=meeting_config.MAPPING_PROCESSING_VERSION,
        )
