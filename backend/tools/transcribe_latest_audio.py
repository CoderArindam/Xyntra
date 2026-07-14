"""Developer CLI utility to transcribe the latest processed audio.

This tool is NOT part of the production runtime. It is intended strictly for
local development and manual verification of the STT pipeline phase.
It locates the most recent WAV file, reconstructs a ProcessedAudio artifact,
and feeds it to the TranscriptionService.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Ensure the backend directory is in the Python path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.meeting.artifacts.recording import ProcessedAudio
from app.meeting.config import meeting_config
from app.meeting.processing.transcription_service import TranscriptionService
from app.meeting.providers.stt.faster_whisper_provider import FasterWhisperProvider


async def get_latest_processed_audio(audio_dir: Path) -> Path | None:
    """Find the most recently created .wav file in the processed_audio directory structure."""
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
    """Reconstruct a ProcessedAudio artifact for testing."""
    session_id = file_path.parent.name
    
    # We don't have the original FFmpeg probe details saved easily here without a DB,
    # but we can fake enough for the transcription service to work since faster-whisper
    # only needs `file_path`.
    
    return ProcessedAudio(
        meeting_id=session_id,
        parent_recording_id="fake-parent-id",
        file_path=str(file_path),
        storage_uri=file_path.resolve().as_uri(),
        duration_seconds=0.0, # Not strictly needed for STT 
        format="wav",
        codec="pcm_s16le",
        sample_rate=16000,
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
    parser = argparse.ArgumentParser(description="Transcribe latest processed audio.")
    args = parser.parse_args()

    print("=" * 60)
    print("KAIO Developer Tool: Transcription Pipeline (M2.3)")
    print("=" * 60)

    audio_dir = Path(meeting_config.PROCESSING_OUTPUT_DIR)
    
    print("\n[0] Locating latest processed audio...")
    latest_file = await get_latest_processed_audio(audio_dir)
    
    if not latest_file:
        print(f"    [ERROR] No processed audio found in {audio_dir}")
        sys.exit(1)
        
    print(f"    [OK] Found latest audio: {latest_file.name}")
    print(f"    Session ID: {latest_file.parent.name}")

    print("\n[1] Initializing STT Provider...")
    provider = FasterWhisperProvider()
    service = TranscriptionService(provider)

    # 3. Reconstruct Artifact
    processed_artifact = await reconstruct_processed_audio(latest_file)

    # 4. Run STT Pipeline
    print("\n[2] Executing Transcription...")
    print("    Running faster-whisper (this may take a few minutes)...")
    
    try:
        raw_transcript = await service.process(processed_artifact)
    except Exception as exc:
        print(f"\n    [ERROR] Transcription Failed: {exc}")
        sys.exit(1)

    # 5. Persist the artifact JSON manually
    out_path = latest_file.parent / "raw_transcript_v1.json"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(raw_transcript.model_dump_json(indent=2))

    # 6. Summary
    print("\n[3] Pipeline Execution Summary")
    print("-" * 60)
    print(f"    Status:         [OK] SUCCESS")
    print(f"    Artifact ID:    {raw_transcript.id}")
    print(f"    Meeting ID:     {processed_artifact.meeting_id}")
    print(f"    Language:       {raw_transcript.detected_language} ({raw_transcript.language_probability*100:.1f}%)")
    print(f"    Model:          {raw_transcript.model_name}")
    print(f"    Segments:       {len(raw_transcript.segments)}")
    print(f"    Process Time:   {raw_transcript.transcription_duration_ms} ms")
    print(f"    Output JSON:    {out_path}")
    print("=" * 60)

    print("\nPreview of first 3 segments:")
    for i, seg in enumerate(raw_transcript.segments[:3]):
        print(f"  [{seg.start_time:.2f}s -> {seg.end_time:.2f}s] {seg.text}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        # Force stdout to utf-8 so printing Bengali/Unicode segments doesn't crash CP1252 terminals
        sys.stdout.reconfigure(encoding='utf-8')
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTranscription cancelled by user.")
        sys.exit(0)
