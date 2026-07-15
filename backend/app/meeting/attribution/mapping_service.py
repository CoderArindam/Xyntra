"""SpeakerMappingService — produces a SpeakerMapping from SpeakerTimeline + ParticipantRoster.

In M2.5 the mapping strategy is "unknown": every speaker label gets
participant_id=None and mapping_confidence=0.0.

The schema is designed so future strategies slot in as new mapping_source
values without any schema changes:

  "unknown"           — M2.5 baseline (no identity resolution)
  "join_order"        — correlate first-speaker to first-joiner
  "voice_embedding"   — cosine similarity against voice fingerprint store
  "ai_reasoning"      — LLM inference from transcript context
  "manual"            — human correction via UI

SpeakerAttributionService never performs mapping.
SpeakerMappingService never performs attribution.
"""

from __future__ import annotations

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
from app.meeting.exceptions import SpeakerMappingError
from app.meeting.logger import get_logger

log = get_logger("attribution.mapping")


class SpeakerMappingService:
    """Produces a SpeakerMapping artifact from diarization and roster data.

    M2.5 baseline: emits one entry per unique speaker label with all
    participant fields null and mapping_source="unknown".

    Future strategies are added by subclassing or injecting a resolution
    callable — this class never needs to change for new strategies.
    """

    async def build(
        self,
        timeline: SpeakerTimeline,
        roster: Optional[ParticipantRoster],
    ) -> SpeakerMapping:
        log.info(
            "attribution.mapping.started",
            meeting_id=timeline.meeting_id,
            timeline_id=timeline.id,
            roster_id=roster.id if roster else None,
            speaker_count=timeline.speaker_count,
        )

        t0 = time.monotonic()

        try:
            # Collect unique speaker labels in the order they first appear
            seen: dict[str, None] = {}
            for turn in timeline.turns:
                seen.setdefault(turn.speaker_label, None)

            entries = [
                SpeakerMappingEntry(
                    speaker_label=label,
                    participant_id=None,
                    participant_name=None,
                    mapping_confidence=0.0,
                    mapping_source="unknown",
                )
                for label in seen
            ]

        except Exception as exc:
            log.error(
                "attribution.mapping.failed",
                meeting_id=timeline.meeting_id,
                error=str(exc),
            )
            raise SpeakerMappingError(f"Speaker mapping failed: {exc}") from exc

        duration_ms = int((time.monotonic() - t0) * 1000)

        artifact = SpeakerMapping(
            meeting_id=timeline.meeting_id,
            parent_speaker_timeline_id=timeline.id,
            parent_participant_roster_id=roster.id if roster else None,
            mapping_strategy="unknown",
            entries=entries,
            processing_version=meeting_config.MAPPING_PROCESSING_VERSION,
        )

        log.info(
            "attribution.mapping.completed",
            meeting_id=timeline.meeting_id,
            artifact_id=artifact.id,
            entry_count=len(entries),
            duration_ms=duration_ms,
        )
        log.info(
            "meeting.artifact.generated",
            artifact_type="SpeakerMapping",
            artifact_id=artifact.id,
            meeting_id=timeline.meeting_id,
        )

        return artifact
