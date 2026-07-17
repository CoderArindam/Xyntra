"""Developer CLI utility to resolve a transcript using a strategy.

Locates the latest speaker_attributed_transcript.json and participant_roster.json,
runs SpeakerMappingService, then SpeakerAttributionService.resolve(),
and writes participant_attributed_transcript.json.

Usage:
    cd backend
    python tools/resolve_latest_transcript.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.meeting.artifacts.speaker import (
    ParticipantRoster,
    SpeakerAttributedTranscript,
    SpeakerTimeline,
)
from app.meeting.attribution.service import SpeakerAttributionService
from app.meeting.mapping.service import SpeakerMappingService
from app.meeting.config import meeting_config

def _find_latest(base_dir: Path, filename: str) -> Path | None:
    candidates = list(base_dir.rglob(filename))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)

async def main() -> None:
    print("=" * 60)
    print("KAIO Developer Tool: Speaker Identity Resolution (M2.7)")
    print("=" * 60)

    storage_dir = Path("storage") / "meeting"

    # ------------------------------------------------------------------ #
    # Locate artifacts                                                     #
    # ------------------------------------------------------------------ #
    print("\n[0] Locating artifacts ...")

    attributed_path = _find_latest(storage_dir, "speaker_attributed_transcript.json")
    if not attributed_path:
        print(f"    [ERROR] No speaker_attributed_transcript.json in {storage_dir}")
        sys.exit(1)
    
    timeline_path = _find_latest(storage_dir, "speaker_timeline.json")
    if not timeline_path:
        print(f"    [ERROR] No speaker_timeline.json in {storage_dir}")
        sys.exit(1)

    roster_path = _find_latest(storage_dir, "participant_roster.json")
    if not roster_path:
        print(f"    [WARN] No participant_roster.json found. Using empty roster.")

    print(f"    [OK] Attributed: {attributed_path.name}")
    print(f"    [OK] Timeline:   {timeline_path.name}")
    if roster_path:
        print(f"    [OK] Roster:     {roster_path.name}")

    # ------------------------------------------------------------------ #
    # Deserialize                                                          #
    # ------------------------------------------------------------------ #
    print("\n[1] Loading artifacts ...")

    try:
        attributed = SpeakerAttributedTranscript.model_validate_json(
            attributed_path.read_text(encoding="utf-8")
        )
        timeline = SpeakerTimeline.model_validate_json(
            timeline_path.read_text(encoding="utf-8")
        )
        roster = None
        if roster_path:
            roster = ParticipantRoster.model_validate_json(
                roster_path.read_text(encoding="utf-8")
            )
    except Exception as exc:
        print(f"    [ERROR] Failed to parse artifacts: {exc}")
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # Build Mapping                                                        #
    # ------------------------------------------------------------------ #
    print(f"\n[2] Building SpeakerMapping (Strategy: {meeting_config.MAPPING_STRATEGY}) ...")
    mapping_service = SpeakerMappingService()
    t0 = time.monotonic()
    
    try:
        mapping = await mapping_service.build(timeline, roster)
    except Exception as exc:
        print(f"\n    [ERROR] Mapping failed: {exc}")
        sys.exit(1)

    out_mapping_path = timeline_path.parent / "speaker_mapping.json"
    out_mapping_path.write_text(mapping.model_dump_json(indent=2), encoding="utf-8")

    # ------------------------------------------------------------------ #
    # Resolve Identities                                                   #
    # ------------------------------------------------------------------ #
    print("\n[3] Resolving Identities ...")
    resolve_service = SpeakerAttributionService()
    
    try:
        participant_attributed = await resolve_service.resolve(attributed, mapping)
    except Exception as exc:
        print(f"\n    [ERROR] Resolution failed: {exc}")
        sys.exit(1)
        
    t1 = time.monotonic()
    runtime_ms = int((t1 - t0) * 1000)

    out_path = attributed_path.parent / "participant_attributed_transcript.json"
    out_path.write_text(participant_attributed.model_dump_json(indent=2), encoding="utf-8")

    # ------------------------------------------------------------------ #
    # Display                                                              #
    # ------------------------------------------------------------------ #
    resolved_segments = [s for s in participant_attributed.segments if s.participant_name]
    unresolved_segments = [s for s in participant_attributed.segments if not s.participant_name]

    print(f"\n[4] Resolution Summary")
    print("-" * 60)
    print(f"    Resolved speakers:   {mapping.resolved_count}/{mapping.speaker_count}")
    print(f"    Strategy:            {mapping.mapping_strategy}")
    print(f"    Runtime:             {runtime_ms} ms")
    
    print("\n    Participant Transcript Preview:")
    for seg in participant_attributed.segments[:8]:
        name = seg.participant_name or seg.speaker_label or "(unresolved)"
        text = seg.text[:60] + "..." if len(seg.text) > 60 else seg.text
        print(f"      [{seg.start_time:.2f}s] {name}:")
        print(f"        {text}")

    print("=" * 60)

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
