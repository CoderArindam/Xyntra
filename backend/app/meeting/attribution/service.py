"""SpeakerAttributionService — two-stage transcript attribution.

Stage 1 — align():
    NormalizedTranscript + SpeakerTimeline → SpeakerAttributedTranscript
    Matches each transcript segment to the best-overlapping SpeakerTurn.
    Produces anonymous labels only (Speaker_01…). No participant names.

Stage 2 — resolve():
    SpeakerAttributedTranscript + SpeakerMapping → ParticipantAttributedTranscript
    Applies a pre-built SpeakerMapping to assign participant identities.
    speaker_label is always preserved alongside participant_name.

This service depends only on abstract contracts and artifact types.
PyannoteProvider is never imported here.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import List, Optional

from app.meeting.artifacts.speaker import (
    ParticipantAttributedSegment,
    ParticipantAttributedTranscript,
    SpeakerAttributedSegment,
    SpeakerAttributedTranscript,
    SpeakerMapping,
    SpeakerTimeline,
    SpeakerTurn,
    ParticipantRoster,
    ParticipantPresenceTimeline,
    MeetingParticipant,
)
from app.meeting.artifacts.attribution_debug import (
    AttributionDebugArtifact,
    AttributionTimelineArtifact,
)
from app.meeting.attribution.dynamic_engine import DynamicAttributionEngine
from app.meeting.artifacts.transcript import NormalizedTranscript, NormalizedTranscriptSegment
from app.meeting.config import meeting_config
from app.meeting.exceptions import SpeakerAttributionError
from app.meeting.logger import get_logger

log = get_logger("attribution.service")

class SpeakerAttributionService:
    """Performs participant identity resolution using DynamicAttributionEngine."""

    async def resolve_with_debug(
        self,
        attributed: SpeakerAttributedTranscript,
        mapping: Optional[SpeakerMapping] = None,
        roster: Optional[ParticipantRoster] = None,
        presence_timeline: Optional[ParticipantPresenceTimeline] = None,
    ) -> Tuple[ParticipantAttributedTranscript, AttributionDebugArtifact, AttributionTimelineArtifact]:
        """Perform dynamic per-turn attribution and return transcript with debug artifacts."""
        log.info(
            "attribution.resolution.started",
            meeting_id=attributed.meeting_id,
            attributed_transcript_id=attributed.id,
            mapping_id=mapping.id if mapping else None,
            roster_id=roster.id if roster else None,
        )

        start_dt = datetime.now(timezone.utc)
        t0 = time.monotonic()

        try:
            participants: List[MeetingParticipant] = []
            if roster and roster.participants:
                participants = [p for p in roster.participants if not p.is_bot and p.participant_id != "UNKNOWN_PARTICIPANT"]
            elif mapping and mapping.entries:
                seen_ids = set()
                for idx, entry in enumerate(mapping.entries):
                    if (
                        entry.participant_id 
                        and entry.participant_id != "UNKNOWN_PARTICIPANT" 
                        and entry.participant_id not in seen_ids
                    ):
                        seen_ids.add(entry.participant_id)
                        participants.append(
                            MeetingParticipant(
                                participant_id=entry.participant_id,
                                display_name=entry.participant_name or entry.participant_id,
                                join_time="2026-01-01T00:00:00Z",
                                join_order=idx + 1,
                            )
                        )

            engine = DynamicAttributionEngine()
            resolved_segments, debug_artifact, timeline_artifact = engine.attribute(
                attributed_segments=attributed.segments,
                participants=participants,
                mapping=mapping,
                presence_timeline=presence_timeline,
                meeting_id=attributed.meeting_id,
            )
            unresolved = sum(1 for s in resolved_segments if s.participant_id is None)

        except Exception as exc:
            log.error(
                "attribution.resolution.failed",
                meeting_id=attributed.meeting_id,
                error=str(exc),
            )
            raise SpeakerAttributionError(f"Speaker resolution failed: {exc}") from exc

        if len(resolved_segments) != len(attributed.segments):
            log.error(
                "attribution.resolution.segment_mismatch",
                meeting_id=attributed.meeting_id,
                input_segments=len(attributed.segments),
                output_segments=len(resolved_segments),
            )
            raise SpeakerAttributionError(
                f"Segment count mismatch during resolution! "
                f"Input: {len(attributed.segments)}, Output: {len(resolved_segments)}"
            )

        end_dt = datetime.now(timezone.utc)
        duration_ms = int((time.monotonic() - t0) * 1000)

        artifact = ParticipantAttributedTranscript(
            meeting_id=attributed.meeting_id,
            parent_speaker_attributed_transcript_id=attributed.id,
            parent_speaker_mapping_id=mapping.id if mapping else None,
            segments=resolved_segments,
            unresolved_speaker_count=unresolved,
            resolution_started_at=start_dt.isoformat(),
            resolution_completed_at=end_dt.isoformat(),
            resolution_duration_ms=duration_ms,
            processing_version=meeting_config.ATTRIBUTION_PROCESSING_VERSION,
        )

        from app.meeting.normalization.validator import TranscriptIntegrityValidator
        validator = TranscriptIntegrityValidator()
        integrity_res = validator.validate_speaker_to_participant(attributed, artifact)
        validator.raise_for_errors(integrity_res)

        log.info(
            "attribution.resolution.completed",
            meeting_id=attributed.meeting_id,
            artifact_id=artifact.id,
            segment_count=len(resolved_segments),
            unresolved=unresolved,
            duration_ms=duration_ms,
        )
        log.info(
            "meeting.artifact.generated",
            artifact_type="ParticipantAttributedTranscript",
            artifact_id=artifact.id,
            meeting_id=attributed.meeting_id,
        )

        return artifact, debug_artifact, timeline_artifact

    async def resolve(
        self,
        attributed: SpeakerAttributedTranscript,
        mapping: Optional[SpeakerMapping] = None,
        roster: Optional[ParticipantRoster] = None,
        presence_timeline: Optional[ParticipantPresenceTimeline] = None,
    ) -> ParticipantAttributedTranscript:
        """Perform dynamic per-turn attribution to produce participant-attributed segments."""
        artifact, _, _ = await self.resolve_with_debug(
            attributed=attributed,
            mapping=mapping,
            roster=roster,
            presence_timeline=presence_timeline,
        )
        return artifact
