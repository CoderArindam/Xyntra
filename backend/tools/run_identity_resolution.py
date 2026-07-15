"""Recommended CLI tool to resolve a transcript using providers and strategy.

Locates the latest speaker_attributed_transcript.json and speaker_timeline.json.
Loads the ParticipantRoster via the configured ParticipantRosterProvider.
Runs SpeakerMappingService, then SpeakerAttributionService.resolve(),
and writes participant_attributed_transcript.json.

Usage:
    cd backend
    python tools/run_identity_resolution.py
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.meeting.artifacts.speaker import (
    SpeakerAttributedTranscript,
    SpeakerTimeline,
)
from app.meeting.attribution.service import SpeakerAttributionService
from app.meeting.mapping.service import SpeakerMappingService
from app.meeting.config import meeting_config
from app.meeting.providers.participant_roster import get_roster_provider

def _find_latest(base_dir: Path, filename: str) -> Path | None:
    candidates = list(base_dir.rglob(filename))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)

async def main() -> None:
    recordings_dir = Path(meeting_config.RECORDING_OUTPUT_DIR)
    processed_dir = Path(meeting_config.PROCESSING_OUTPUT_DIR)

    # ------------------------------------------------------------------ #
    # Locate artifacts                                                     #
    # ------------------------------------------------------------------ #
    attributed_path = _find_latest(recordings_dir, "speaker_attributed_transcript.json")
    if not attributed_path:
        print(f"[ERROR] No speaker_attributed_transcript.json in {recordings_dir}")
        sys.exit(1)
    
    timeline_path = _find_latest(processed_dir, "speaker_timeline.json")
    if not timeline_path:
        print(f"[ERROR] No speaker_timeline.json in {processed_dir}")
        sys.exit(1)

    try:
        attributed = SpeakerAttributedTranscript.model_validate_json(
            attributed_path.read_text(encoding="utf-8")
        )
        timeline = SpeakerTimeline.model_validate_json(
            timeline_path.read_text(encoding="utf-8")
        )
    except Exception as exc:
        print(f"[ERROR] Failed to parse artifacts: {exc}")
        sys.exit(1)

    meeting_id = timeline.meeting_id
    original_segment_count = len(attributed.segments)

    # ------------------------------------------------------------------ #
    # Fetch Roster via Provider                                            #
    # ------------------------------------------------------------------ #
    provider = get_roster_provider()
    try:
        roster = await provider.get_roster(meeting_id)
    except Exception as exc:
        print(f"[ERROR] Provider failed: {exc}")
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # Build Mapping                                                        #
    # ------------------------------------------------------------------ #
    mapping_service = SpeakerMappingService()
    try:
        mapping = await mapping_service.build(timeline, roster)
    except Exception as exc:
        print(f"[ERROR] Mapping failed: {exc}")
        sys.exit(1)

    out_mapping_path = timeline_path.parent / "speaker_mapping.json"
    out_mapping_path.write_text(mapping.model_dump_json(indent=2), encoding="utf-8")

    # ------------------------------------------------------------------ #
    # Resolve Identities                                                   #
    # ------------------------------------------------------------------ #
    resolve_service = SpeakerAttributionService()
    try:
        participant_attributed = await resolve_service.resolve(attributed, mapping)
    except Exception as exc:
        print(f"[ERROR] Resolution failed: {exc}")
        sys.exit(1)

    out_path = attributed_path.parent / "participant_attributed_transcript.json"
    out_path.write_text(participant_attributed.model_dump_json(indent=2), encoding="utf-8")

    # ------------------------------------------------------------------ #
    # Validation                                                           #
    # ------------------------------------------------------------------ #
    resolved_segment_count = len(participant_attributed.segments)
    if resolved_segment_count != original_segment_count:
        print(f"[CRITICAL ERROR] Segment mismatch! Input: {original_segment_count} Output: {resolved_segment_count}")
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # Display Format                                                       #
    # ------------------------------------------------------------------ #
    avg_conf = sum(e.mapping_confidence or 0.0 for e in mapping.entries) / max(1, len(mapping.entries))
    resolved_speakers = mapping.resolved_count
    total_speakers = mapping.speaker_count
    participants_count = mapping.participant_count

    print("====================================================")
    print("KAIO Identity Resolution Report")
    print("====================================================\n")

    print("Meeting ID:")
    print(f"{meeting_id}\n")

    print("Participants:")
    print(f"{participants_count}\n")

    print("Detected Speakers:")
    print(f"{total_speakers}\n")

    print("Resolved Speakers:")
    print(f"{resolved_speakers} / {total_speakers}\n")

    print("Transcript Segments:")
    print(f"{original_segment_count}\n")

    print("Resolved Segments:")
    print(f"{original_segment_count} / {original_segment_count}\n")

    print("Strategy:")
    print(f"{mapping.mapping_strategy}\n")

    print("Average Mapping Confidence:")
    print(f"{avg_conf:.2f}\n")

    print("Output:")
    print(f"{out_path}\n")

    print("====================================================")
    print("Conversation Preview\n")

    for seg in participant_attributed.segments[:8]:
        name = seg.participant_name or seg.speaker_label or "(unresolved)"
        text = seg.text[:80] + "..." if len(seg.text) > 80 else seg.text
        m, s = divmod(int(seg.start_time), 60)
        print(f"[{m:02d}:{s:02d}]")
        print(f"{name}:")
        print(f"{text}\n")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
