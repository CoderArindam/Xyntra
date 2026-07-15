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
from typing import Optional

from app.meeting.artifacts.speaker import (
    ParticipantAttributedSegment,
    ParticipantAttributedTranscript,
    SpeakerAttributedSegment,
    SpeakerAttributedTranscript,
    SpeakerMapping,
    SpeakerTimeline,
    SpeakerTurn,
)
from app.meeting.artifacts.transcript import NormalizedTranscript, NormalizedTranscriptSegment
from app.meeting.config import meeting_config
from app.meeting.exceptions import SpeakerAttributionError
from app.meeting.logger import get_logger

log = get_logger("attribution.service")

class SpeakerAttributionService:
    """Performs participant identity resolution.
    
    Stage 1 align() was moved to alignment.service.
    """

    # ------------------------------------------------------------------ #
    # Stage 2 — resolve                                                    #
    # ------------------------------------------------------------------ #

    async def resolve(
        self,
        attributed: SpeakerAttributedTranscript,
        mapping: Optional[SpeakerMapping],
    ) -> ParticipantAttributedTranscript:
        """Apply a SpeakerMapping to produce participant-attributed segments.

        speaker_label is always preserved. participant_* fields are nullable
        when no mapping entry exists for a label or mapping is None.
        The SpeakerMapping is never modified here — it is consumed read-only.
        """
        log.info(
            "attribution.resolution.started",
            meeting_id=attributed.meeting_id,
            attributed_transcript_id=attributed.id,
            mapping_id=mapping.id if mapping else None,
        )

        start_dt = datetime.now(timezone.utc)
        t0 = time.monotonic()

        try:
            # Build a fast lookup from speaker_label → mapping entry
            label_map: dict[str, tuple[Optional[str], Optional[str], Optional[float]]] = {}
            if mapping:
                for entry in mapping.entries:
                    label_map[entry.speaker_label] = (
                        entry.participant_id,
                        entry.participant_name,
                        entry.mapping_confidence,
                    )

            resolved_segments: list[ParticipantAttributedSegment] = []
            unresolved = 0

            for seg in attributed.segments:
                pid, pname, mconf = label_map.get(seg.speaker_label or "", (None, None, None))
                if pid is None and seg.speaker_label is not None:
                    unresolved += 1

                resolved_segments.append(
                    ParticipantAttributedSegment(
                        segment_id=seg.segment_id,
                        start_time=seg.start_time,
                        end_time=seg.end_time,
                        text=seg.text,
                        speaker_label=seg.speaker_label,           # always preserved
                        speaker_label_confidence=seg.diarization_confidence,
                        participant_id=pid,
                        participant_name=pname,
                        mapping_confidence=mconf,
                        language=seg.language,
                    )
                )

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

        return artifact
