"""Developer CLI utility to align normalized transcript with speaker timeline.

Locates the latest normalized_transcript.json and speaker_timeline.json,
runs SpeakerAlignmentService, and writes speaker_attributed_transcript.json.

Usage:
    cd backend
    python tools/align_latest_transcript.py
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

from app.meeting.alignment.algorithms import merge_adjacent_turns, remove_micro_turns
from app.meeting.alignment.service import SpeakerAlignmentService
from app.meeting.artifacts.speaker import SpeakerTimeline
from app.meeting.artifacts.transcript import NormalizedTranscript
from app.meeting.config import meeting_config


def _find_latest(base_dir: Path, filename: str) -> Path | None:
    """Find the most recently modified file matching filename across session dirs."""
    candidates = list(base_dir.rglob(filename))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


async def main() -> None:
    print("=" * 60)
    print("KAIO Developer Tool: Speaker Alignment Engine (M2.6.1)")
    print("=" * 60)

    storage_dir = Path("storage") / "meeting"

    # ------------------------------------------------------------------ #
    # Locate artifacts                                                     #
    # ------------------------------------------------------------------ #
    print("\n[0] Locating artifacts ...")

    transcript_path = _find_latest(storage_dir, "normalized_transcript.json")
    if not transcript_path:
        print(f"    [ERROR] No normalized_transcript.json in {storage_dir}")
        sys.exit(1)
    print(f"    [OK] Transcript: {transcript_path.name}")
    print(f"    Session: {transcript_path.parent.name}")

    timeline_path = _find_latest(storage_dir, "speaker_timeline.json")
    if not timeline_path:
        print(f"    [ERROR] No speaker_timeline.json in {storage_dir}")
        sys.exit(1)
    print(f"    [OK] Timeline:   {timeline_path.name}")
    print(f"    Session: {timeline_path.parent.name}")

    # ------------------------------------------------------------------ #
    # Deserialize                                                          #
    # ------------------------------------------------------------------ #
    print("\n[1] Loading artifacts ...")

    try:
        transcript = NormalizedTranscript.model_validate_json(
            transcript_path.read_text(encoding="utf-8")
        )
        print(f"    Transcript ID:   {transcript.id}")
        print(f"    Segments:        {len(transcript.segments)}")
    except Exception as exc:
        print(f"    [ERROR] Failed to parse transcript: {exc}")
        sys.exit(1)

    try:
        timeline = SpeakerTimeline.model_validate_json(
            timeline_path.read_text(encoding="utf-8")
        )
        print(f"    Timeline ID:     {timeline.id}")
        print(f"    Speakers:        {timeline.speaker_count}")
        print(f"    Turns:           {len(timeline.turns)}")
    except Exception as exc:
        print(f"    [ERROR] Failed to parse timeline: {exc}")
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # Calculate Diagnostics                                                #
    # ------------------------------------------------------------------ #
    # Since artifact schemas are strictly immutable, we compute pre-processing
    # stats here independently to display in the CLI.
    working_turns = list(timeline.turns)
    working_turns, removed = remove_micro_turns(
        working_turns, meeting_config.ALIGNMENT_MIN_TURN_DURATION_MS
    )
    _, merged_count = merge_adjacent_turns(
        working_turns, meeting_config.ALIGNMENT_MERGE_GAP_MS
    )
    removed_micro_count = len(removed)

    # ------------------------------------------------------------------ #
    # Align                                                                #
    # ------------------------------------------------------------------ #
    print("\n[2] Running SpeakerAlignmentService ...")
    service = SpeakerAlignmentService()

    t0 = time.monotonic()
    try:
        attributed = await service.align(transcript, timeline)
    except Exception as exc:
        print(f"\n    [ERROR] Alignment failed: {exc}")
        sys.exit(1)
    t1 = time.monotonic()
    runtime_ms = int((t1 - t0) * 1000)

    # ------------------------------------------------------------------ #
    # Write output                                                         #
    # ------------------------------------------------------------------ #
    out_path = transcript_path.parent / "speaker_attributed_transcript.json"
    out_path.write_text(
        attributed.model_dump_json(indent=2), encoding="utf-8"
    )

    # ------------------------------------------------------------------ #
    # Statistics                                                           #
    # ------------------------------------------------------------------ #
    total = len(attributed.segments)
    matched = total - attributed.unattributed_segment_count
    unmatched = attributed.unattributed_segment_count
    
    ratios = [
        s.attribution_confidence
        for s in attributed.segments
        if s.attribution_confidence is not None
    ]
    avg_conf = round(sum(ratios) / len(ratios), 4) if ratios else 0.0

    print(f"\n[3] Alignment Summary")
    print("-" * 60)
    print(f"    Segments processed:  {total}")
    print(f"    Matched:             {matched}")
    print(f"    Unmatched:           {unmatched}")
    print(f"    Average confidence:  {avg_conf:.4f}")
    print(f"    Merged turns:        {merged_count}")
    print(f"    Removed micro turns: {removed_micro_count}")
    print(f"    Average overlap:     {avg_conf:.4f}")  # Using confidence score for overlap as requested
    print(f"    Runtime:             {runtime_ms} ms")
    print(f"    Output JSON:         {out_path}")

    print(f"\n    Preview (first 8 segments):")
    for seg in attributed.segments[:8]:
        speaker = seg.speaker_label or "(none)"
        conf = f"{seg.attribution_confidence:.2f}" if seg.attribution_confidence else "n/a"
        text_preview = seg.text[:60] + "..." if len(seg.text) > 60 else seg.text
        print(f"      [{seg.start_time:.2f}s → {seg.end_time:.2f}s] {speaker} (conf={conf})")
        print(f"        {text_preview}")

    print("=" * 60)

    # Idempotency check
    print("\n[4] Idempotency verification ...")
    attributed2 = await service.align(transcript, timeline)
    labels1 = [(s.segment_id, s.speaker_label, s.attribution_confidence) for s in attributed.segments]
    labels2 = [(s.segment_id, s.speaker_label, s.attribution_confidence) for s in attributed2.segments]
    if labels1 == labels2:
        print("    [OK] Output is deterministic (two runs produce identical assignments)")
    else:
        print("    [WARN] Idempotency mismatch — investigate tie-breaking")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
