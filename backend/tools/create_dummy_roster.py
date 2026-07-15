"""Developer CLI utility to generate a dummy ParticipantRoster artifact.

Usage:
    cd backend
    python tools/create_dummy_roster.py --names "Arindam,Samina,Rahul"
"""

import argparse
import asyncio
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.meeting.artifacts.speaker import ParticipantRoster, MeetingParticipant
from app.meeting.config import meeting_config

def _find_latest_session(base_dir: Path) -> Path | None:
    """Find the most recently modified session directory."""
    dirs = [d for d in base_dir.iterdir() if d.is_dir()]
    if not dirs:
        return None
    return max(dirs, key=lambda d: d.stat().st_mtime)

async def main() -> None:
    parser = argparse.ArgumentParser(description="Create a dummy participant roster.")
    parser.add_argument(
        "--names",
        type=str,
        default="Arindam,Samina",
        help="Comma-separated list of participant names (e.g. Arindam,Samina).",
    )
    args = parser.parse_args()

    names = [n.strip() for n in args.names.split(",") if n.strip()]
    if not names:
        print("[ERROR] No valid names provided.")
        sys.exit(1)

    print("=" * 60)
    print("KAIO Developer Tool: Create Dummy Roster")
    print("=" * 60)

    processed_dir = Path(meeting_config.PROCESSING_OUTPUT_DIR)
    session_dir = _find_latest_session(processed_dir)
    if not session_dir:
        print(f"[ERROR] No session directories found in {processed_dir}")
        sys.exit(1)

    print(f"\n[0] Target Session: {session_dir.name}")

    start_dt = datetime.now(timezone.utc)
    participants = []
    
    for i, name in enumerate(names):
        participants.append(
            MeetingParticipant(
                participant_id=f"dummy_{name.lower()}_{uuid4().hex[:8]}",
                display_name=name,
                join_order=i + 1,
                join_time=start_dt.isoformat(),
                is_host=(i == 0),
            )
        )

    roster = ParticipantRoster(
        meeting_id=session_dir.name,
        source="dummy",
        participants=participants,
        captured_at=start_dt.isoformat(),
        processing_version="1.0.0",
    )

    out_path = session_dir / "participant_roster.json"
    out_path.write_text(roster.model_dump_json(indent=2), encoding="utf-8")

    print("\n[1] Artifact Generated")
    print("-" * 60)
    print(f"    Roster ID:    {roster.id}")
    print(f"    Meeting ID:   {roster.meeting_id}")
    print(f"    Participants: {len(participants)}")
    for p in participants:
        print(f"      - {p.display_name} (Host: {p.is_host})")
    print(f"    Saved to:     {out_path}")
    print("=" * 60)

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
