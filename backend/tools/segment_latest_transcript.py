"""Developer CLI utility to run ConversationTurnSegmenter on the latest transcript.

Usage:
    cd backend
    python tools/segment_latest_transcript.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.meeting.artifacts.transcript import NormalizedTranscript
from app.meeting.segmentation.service import ConversationTurnSegmenter


def _find_latest_transcript(storage_dir: Path) -> Path | None:
    candidates = list(storage_dir.rglob("normalized_transcript.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def main() -> None:
    print("=" * 60)
    print("KAIO Developer Tool: Conversation Turn Segmenter (Phase 2)")
    print("=" * 60)

    storage_dir = Path("storage") / "meeting"
    print(f"\n[0] Locating latest normalized_transcript.json in {storage_dir} ...")

    path = _find_latest_transcript(storage_dir)
    if not path:
        print(f"    [ERROR] No normalized_transcript.json found in {storage_dir}")
        sys.exit(1)

    print(f"    [OK] Found: {path}")

    raw_data = json.loads(path.read_text(encoding="utf-8"))
    transcript = NormalizedTranscript.model_validate(raw_data)

    print(f"    Input segments: {len(transcript.segments)}")

    print("\n[1] Running ConversationTurnSegmenter ...")
    segmenter = ConversationTurnSegmenter()
    segmented = segmenter.segment(transcript)

    print(f"    [OK] Segmentation completed.")

    print("\n[2] Segmentation Summary")
    print("-" * 60)
    print(f"    Input Segments:      {len(transcript.segments)}")
    print(f"    Output Segments:     {len(segmented.segments)}")
    
    switches = sum(1 for s in segmented.segments if s.metadata.get("candidate_speaker_switch"))
    print(f"    Candidate Switches:  {switches}")

    print("\n    Segment Preview:")
    for seg in segmented.segments:
        switch_str = ""
        if seg.metadata.get("candidate_speaker_switch"):
            reason = seg.metadata.get("speaker_switch_reason", "unknown")
            switch_str = f" [CANDIDATE SWITCH: {reason}]"
        print(f"      [{seg.start_time:.2f}s → {seg.end_time:.2f}s] {seg.text}{switch_str}")

    print("=" * 60)


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    main()
