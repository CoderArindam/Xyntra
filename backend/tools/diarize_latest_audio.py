"""Developer CLI utility to diarize the latest processed audio.

This tool is NOT part of the production runtime. It is intended strictly
for local development and manual verification of the M2.5 diarization phase.

Pipeline:
  1. Locate latest .wav file in processed_audio storage
  2. Reconstruct a ProcessedAudio artifact (no DB required)
  3. Run PyannoteProvider diarization
  4. Save speaker_timeline.json next to the audio
  5. Print: speaker count, per-speaker durations, timeline preview

Usage:
    cd backend
    python tools/diarize_latest_audio.py

Requires:
    pip install pyannote.audio
    MEETING_DIARIZATION_PYANNOTE_AUTH_TOKEN set in .env
"""

import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.meeting.artifacts.recording import ProcessedAudio
from app.meeting.config import meeting_config
from app.meeting.providers.diarization.pyannote_provider import PyannoteProvider


async def get_latest_processed_audio(audio_dir: Path) -> Path | None:
    if not audio_dir.exists():
        return None
    latest_file = None
    latest_time = 0.0
    for session_dir in audio_dir.iterdir():
        if not session_dir.is_dir():
            continue
        for file_path in session_dir.iterdir():
            if file_path.is_file() and file_path.suffix == ".wav":
                mtime = file_path.stat().st_mtime
                if mtime > latest_time:
                    latest_time = mtime
                    latest_file = file_path
    return latest_file


async def reconstruct_processed_audio(file_path: Path) -> ProcessedAudio:
    session_id = file_path.parent.name
    return ProcessedAudio(
        meeting_id=session_id,
        parent_recording_id="dev-tool-placeholder",
        file_path=str(file_path),
        storage_uri=file_path.resolve().as_uri(),
        duration_seconds=0.0,
        format="wav",
        codec="pcm_s16le",
        sample_rate=16000,
        channels=1,
        bitrate=256000,
        file_size_bytes=file_path.stat().st_size,
        checksum_sha256="dev-tool-placeholder",
        processing_started_at="2026-01-01T00:00:00Z",
        processing_completed_at="2026-01-01T00:00:00Z",
        processing_duration_ms=0,
        processing_version="1.0.0",
    )


async def main() -> None:
    print("=" * 60)
    print("KAIO Developer Tool: Speaker Diarization (M2.5)")
    print("=" * 60)

    audio_dir = Path(meeting_config.PROCESSING_OUTPUT_DIR)

    print("\n[0] Locating latest processed audio...")
    latest_file = await get_latest_processed_audio(audio_dir)
    if not latest_file:
        print(f"    [ERROR] No processed audio found in {audio_dir}")
        sys.exit(1)
    print(f"    [OK] Found: {latest_file.name}")
    print(f"    Session: {latest_file.parent.name}")

    print("\n[1] Initializing Pyannote provider...")
    if not meeting_config.DIARIZATION_PYANNOTE_AUTH_TOKEN:
        print("    [ERROR] MEETING_DIARIZATION_PYANNOTE_AUTH_TOKEN is not set.")
        print("    Set it in .env and re-run.")
        sys.exit(1)
    provider = PyannoteProvider()

    print("\n[2] Reconstructing ProcessedAudio artifact...")
    audio = await reconstruct_processed_audio(latest_file)

    print("\n[3] Running diarization (this may take several minutes)...")
    try:
        timeline = await provider.diarize(audio)
    except Exception as exc:
        print(f"\n    [ERROR] Diarization failed: {exc}")
        sys.exit(1)

    # Save artifact JSON
    out_path = latest_file.parent / "speaker_timeline.json"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(timeline.model_dump_json(indent=2))

    # Compute per-speaker durations
    speaker_durations: dict[str, float] = defaultdict(float)
    for turn in timeline.turns:
        speaker_durations[turn.speaker_label] += turn.end_time - turn.start_time

    print("\n[4] Diarization Summary")
    print("-" * 60)
    print(f"    Artifact ID:      {timeline.id}")
    print(f"    Meeting ID:       {timeline.meeting_id}")
    print(f"    Provider:         {timeline.provider.provider_name} {timeline.provider.provider_version}")
    print(f"    Model:            {timeline.provider.model_name}")
    print(f"    Speakers:         {timeline.speaker_count}")
    print(f"    Total turns:      {len(timeline.turns)}")
    print(f"    Speech duration:  {timeline.total_speech_duration_seconds:.1f}s")
    print(f"    Process time:     {timeline.diarization_duration_ms} ms")
    print(f"    Output JSON:      {out_path}")

    print("\n    Per-speaker durations:")
    for label, dur in sorted(speaker_durations.items()):
        print(f"      {label}: {dur:.1f}s")

    print("\n    Timeline preview (first 10 turns):")
    for turn in timeline.turns[:10]:
        print(f"      [{turn.start_time:.2f}s → {turn.end_time:.2f}s] {turn.speaker_label}")
    if len(timeline.turns) > 10:
        print(f"      ... and {len(timeline.turns) - 10} more turns")

    print("=" * 60)


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDiarization cancelled.")
        sys.exit(0)
