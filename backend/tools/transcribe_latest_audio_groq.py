"""Developer CLI utility to test Groq STT Pipeline.

This tool is NOT part of the production runtime. It is intended strictly for
local development and manual verification of Groq transcription.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure the backend directory is in the Python path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.meeting.artifacts.recording import ProcessedAudio
from app.meeting.config import meeting_config
from app.meeting.providers.stt.groq_provider import GroqProvider

async def get_latest_processed_audio(audio_dir: Path) -> Path | None:
    if not audio_dir.exists():
        return None
    latest_file = None
    latest_time = 0.0
    for session_dir in audio_dir.iterdir():
        if not session_dir.is_dir():
            continue
        for file_path in session_dir.iterdir():
            if file_path.is_file() and file_path.suffix == ".webm":
                mtime = file_path.stat().st_mtime
                if mtime > latest_time:
                    latest_time = mtime
                    latest_file = file_path
    return latest_file

async def reconstruct_processed_audio(file_path: Path) -> ProcessedAudio:
    session_id = file_path.parent.name
    return ProcessedAudio(
        meeting_id=session_id,
        parent_recording_id="fake-parent-id",
        file_path=str(file_path),
        storage_uri=file_path.resolve().as_uri(),
        duration_seconds=0.0,
        format="webm",
        codec="opus",
        sample_rate=48000,
        channels=1,
        bitrate=256000,
        file_size_bytes=file_path.stat().st_size,
        checksum_sha256="fake-checksum",
        processing_started_at="2026-01-01T00:00:00Z",
        processing_completed_at="2026-01-01T00:00:00Z",
        processing_duration_ms=0,
        processing_version="1.0.0",
    )

async def main() -> None:
    parser = argparse.ArgumentParser(description="Test Groq STT with latest processed audio.")
    args = parser.parse_args()

    print("=" * 48)
    print("KAIO Developer Tool")
    print("Groq Speech-to-Text")
    print("=" * 48)

    audio_dir = Path(meeting_config.RECORDING_OUTPUT_DIR)
    
    print("\nLatest Audio")
    latest_file = await get_latest_processed_audio(audio_dir)
    
    if not latest_file:
        print(f"✗ failed - No processed audio found in {audio_dir}")
        sys.exit(1)
        
    print(f"✓ located ({latest_file.name})")

    try:
        provider = GroqProvider()
    except ValueError as e:
        print(f"\n✗ Configuration Error: {e}")
        sys.exit(1)

    processed_artifact = await reconstruct_processed_audio(latest_file)

    print("\nUploading...")
    print("✓ upload completed (Groq SDK handles this in transit)")
    print("\nWaiting for transcription...")
    
    try:
        raw_transcript = await provider.transcribe(processed_artifact)
        print("✓ completed")
    except Exception as exc:
        print(f"\n✗ Transcription Failed: {exc}")
        sys.exit(1)

    json_path = latest_file.parent / "meeting.groq.transcript.json"
    txt_path = latest_file.parent / "meeting.groq.txt"

    with open(json_path, "w", encoding="utf-8") as f:
        f.write(raw_transcript.model_dump_json(indent=2))

    plain_text = "\n".join(seg.text for seg in raw_transcript.segments)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(plain_text)

    duration_m, duration_s = divmod(raw_transcript.transcription_duration_ms // 1000, 60)

    print("\nModel")
    print(raw_transcript.model_name)
    print("\nLanguage")
    print(raw_transcript.detected_language)
    print("\nDuration")
    print(f"{duration_m}m {duration_s}s (execution time)")
    print("\nSegments")
    print(len(raw_transcript.segments))
    
    print("\nTranscript")
    print(f"saved to\n{json_path.name}")
    print("\nPlain text")
    print(f"saved to\n{txt_path.name}")
    
    print(f"\nElapsed Time\n{raw_transcript.transcription_duration_ms / 1000:.1f} seconds")
    print("=" * 48)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTranscription cancelled by user.")
        sys.exit(0)
