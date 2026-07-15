"""Developer CLI utility to normalize the latest RawTranscript.

This tool is NOT part of the production runtime.  It is intended strictly for
local development and manual verification of the normalization pipeline.

It locates the most recent transcript JSON in the recordings directory,
loads it as a RawTranscript artifact, runs TranscriptNormalizationService,
writes normalized_transcript.json alongside the source, and prints a
detailed summary including boundary integrity status.

Usage:
    cd backend
    python tools/normalize_latest_transcript.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.meeting.artifacts.transcript import RawTranscript
from app.meeting.config import meeting_config
from app.meeting.exceptions import TranscriptNormalizationError
from app.meeting.normalization.service import TranscriptNormalizationService


def _find_latest_transcript(recordings_dir: Path) -> Path | None:
    candidates = [
        *recordings_dir.rglob("*.groq.transcript.json"),
        *recordings_dir.rglob("raw_transcript_v1.json"),
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


async def main() -> None:
    print("=" * 60)
    print("KAIO Developer Tool: Transcript Normalization Pipeline (M2.4)")
    print("=" * 60)

    recordings_dir = Path(meeting_config.RECORDING_OUTPUT_DIR)

    print(f"\n[0] Locating latest transcript in {recordings_dir} ...")
    transcript_path = _find_latest_transcript(recordings_dir)

    if not transcript_path:
        print(f"    [ERROR] No transcript JSON found in {recordings_dir}")
        sys.exit(1)

    print(f"    [OK] Found: {transcript_path.name}")
    print(f"    Session:   {transcript_path.parent.name}")

    print("\n[1] Loading RawTranscript artifact ...")
    raw_data = json.loads(transcript_path.read_text(encoding="utf-8"))

    try:
        raw_transcript = RawTranscript.model_validate(raw_data)
    except Exception as exc:
        print(f"    [ERROR] Failed to parse transcript: {exc}")
        sys.exit(1)

    print(f"    [OK] Artifact ID:  {raw_transcript.id}")
    print(f"    Language:          {raw_transcript.detected_language} ({raw_transcript.language_probability*100:.1f}%)")
    print(f"    Model:             {raw_transcript.model_name}")
    print(f"    Input segments:    {len(raw_transcript.segments)}")

    print("\n[2] Running TranscriptNormalizationService ...")
    service = TranscriptNormalizationService()

    try:
        normalized = await service.normalize(raw_transcript)
        boundary_ok = True
        boundary_error = None
    except TranscriptNormalizationError as exc:
        boundary_ok = False
        boundary_error = str(exc)
        normalized = None
    except Exception as exc:
        print(f"\n    [ERROR] Normalization failed: {exc}")
        sys.exit(1)

    if not boundary_ok:
        print(f"\n    [ERROR] Normalization failed with boundary violation:")
        print(f"    {boundary_error}")
        print(f"\n    Boundary Integrity : FAILED")
        sys.exit(1)

    print(f"    [OK] Normalization complete in {normalized.normalization_duration_ms} ms")

    # Write output
    out_path = transcript_path.parent / "normalized_transcript.json"
    out_path.write_text(normalized.model_dump_json(indent=2), encoding="utf-8")

    stats = normalized.statistics
    input_n = stats.total_input_segments
    output_n = stats.total_output_segments
    removed_n = stats.removed_segments

    # Boundary integrity result
    integrity_passed = output_n == (input_n - removed_n)
    integrity_str = "PASSED" if integrity_passed else "FAILED"

    print("\n[3] Normalization Summary")
    print("-" * 60)
    print(f"    Status:              [OK] SUCCESS")
    print(f"    Artifact ID:         {normalized.id}")
    print(f"    Meeting ID:          {normalized.meeting_id}")
    print(f"    Language:            {normalized.language}")
    print(f"    Processing version:  {normalized.processing_version}")
    print(f"    Input Segments:      {input_n}")
    print(f"    Output Segments:     {output_n}")
    print(f"    Segments Removed:    {removed_n}  (whitespace-only)")
    print(f"    Segments Merged:     0  (merging disabled)")
    print(f"    Avg segment length:  {stats.average_segment_length:.1f} chars")
    print(f"    Processing time:     {stats.processing_time_ms} ms")
    print(f"    Boundary Integrity:  {integrity_str}")
    print(f"    Output JSON:         {out_path}")

    print("\n    Rule statistics:")
    for rule_name, count in stats.rule_statistics.items():
        print(f"      {rule_name:<24} {count} segments affected")

    print("=" * 60)

    # Idempotency check
    print("\n[4] Idempotency verification ...")
    normalized2 = await service.normalize(raw_transcript)
    texts1 = [s.text for s in normalized.segments]
    texts2 = [s.text for s in normalized2.segments]
    if texts1 == texts2:
        print("    [OK] Output is deterministic (two runs produce identical segments)")
    else:
        print("    [WARN] Idempotency mismatch — investigate rule order")

    print(f"\nPreview of first 5 normalized segments:")
    for seg in normalized.segments[:5]:
        speaker = seg.speaker or "unknown"
        print(f"  [{seg.start_time:.2f}s → {seg.end_time:.2f}s] ({speaker}) {seg.text}")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
