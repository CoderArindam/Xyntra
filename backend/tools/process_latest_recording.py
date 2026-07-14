"""Developer CLI utility to process the latest meeting recording.

This tool is NOT part of the production runtime. It is intended strictly for
local development and manual verification of the audio processing pipeline.
It automatically locates the most recent recording on disk, reconstructs a
MeetingRecording artifact, validates it, processes it, and prints a summary.
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure the backend directory is in the Python path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.meeting.artifacts.recording import MeetingRecording
from app.meeting.audio.ffmpeg_service import FFmpegService
from app.meeting.config import meeting_config
from app.meeting.exceptions import AudioProcessingError, RecordingValidationError
from app.meeting.processing.service import AudioProcessingService
from app.meeting.processing.validator import RecordingValidator
from app.meeting.recording.storage import LocalRecordingStorage, compute_sha256


async def get_latest_recording_file(recordings_dir: Path) -> Path | None:
    """Find the most recently created file in the recordings directory structure."""
    if not recordings_dir.exists():
        return None

    latest_file = None
    latest_time = 0.0

    # Directory layout is recordings/{session_id}/{file}.webm
    for session_dir in recordings_dir.iterdir():
        if not session_dir.is_dir():
            continue
        for file_path in session_dir.iterdir():
            if file_path.is_file() and not file_path.name.endswith(".tmp"):
                mtime = file_path.stat().st_mtime
                if mtime > latest_time:
                    latest_time = mtime
                    latest_file = file_path

    return latest_file


async def reconstruct_artifact(file_path: Path, ffmpeg: FFmpegService, skip_duration_validation: bool = False) -> MeetingRecording:
    """Reconstruct a MeetingRecording artifact from a physical file on disk."""
    session_id = file_path.parent.name
    
    print(f"\n[1] Inspecting file: {file_path}")
    print("    Probing with ffprobe...")
    
    try:
        probe = await ffmpeg.probe(str(file_path))
    except Exception as exc:
        print(f"    [ERROR] Failed to probe file: {exc}")
        sys.exit(1)
        
    print("    Computing checksum...")
    checksum = compute_sha256(file_path.read_bytes())
    
    # We must fake start/end time since we don't have the original runtime state
    mtime_dt = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
    
    # If probe duration is 0 (streaming WebM) and we want to force validation, mock a valid duration
    artifact_duration = probe.duration_seconds
    if artifact_duration == 0.0 and skip_duration_validation:
        artifact_duration = 9999.0  # Bypass validator min duration check
    
    return MeetingRecording(
        meeting_id=session_id,
        file_path=str(file_path),
        storage_uri=file_path.resolve().as_uri(),
        duration_seconds=artifact_duration,
        format=file_path.suffix.lstrip("."),
        sample_rate=probe.sample_rate or 48000,
        channel_count=probe.channels or 2,
        codec=probe.codec_name or "unknown",
        mime_type=f"audio/{file_path.suffix.lstrip('.')}",
        file_size_bytes=file_path.stat().st_size,
        checksum_sha256=checksum,
        recording_start_time=mtime_dt.isoformat(),
        recording_end_time=mtime_dt.isoformat(),
        recording_status="completed",
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Process latest meeting recording.")
    parser.add_argument("--skip-duration-validation", action="store_true", help="Skip duration validation for streaming recordings")
    parser.add_argument("--force", action="store_true", help="Alias for --skip-duration-validation")
    args = parser.parse_args()
    
    skip_validation = args.skip_duration_validation or args.force

    print("=" * 60)
    print("KAIO Developer Tool: Audio Processing Pipeline (M2.2)")
    if skip_validation:
        print("Mode:           [FORCE] Skipping duration validation")
    print("=" * 60)

    recordings_dir = Path(meeting_config.RECORDING_OUTPUT_DIR)
    
    # 1. Locate recording
    print("\n[0] Locating latest recording...")
    latest_file = await get_latest_recording_file(recordings_dir)
    
    if not latest_file:
        print(f"    [ERROR] No recordings found in {recordings_dir}")
        sys.exit(1)
        
    print(f"    [OK] Found latest recording: {latest_file.name}")
    print(f"    Session ID: {latest_file.parent.name}")
    print(f"    Size: {latest_file.stat().st_size / 1024 / 1024:.2f} MB")

    # 2. Setup Services
    ffmpeg_service = FFmpegService()
    validator = RecordingValidator(ffmpeg=ffmpeg_service)
    
    # The processing service uses a separate storage pointing to the processed output dir
    processing_storage = LocalRecordingStorage(meeting_config.PROCESSING_OUTPUT_DIR)
    
    processor = AudioProcessingService(
        ffmpeg=ffmpeg_service,
        validator=validator,
        storage=processing_storage,
    )

    # 3. Reconstruct Artifact
    recording_artifact = await reconstruct_artifact(latest_file, ffmpeg_service, skip_validation)

    # 4. Run Processing Pipeline
    print("\n[2] Executing Audio Processing Pipeline...")
    
    try:
        # Note: validator.validate() is called internally by processor.process()
        print("    Validating and normalizing audio... (this may take a moment)")
        processed_artifact = await processor.process(recording_artifact)
    except RecordingValidationError as exc:
        print(f"\n    [ERROR] Validation Failed: {exc}")
        sys.exit(1)
    except AudioProcessingError as exc:
        print(f"\n    [ERROR] Processing Failed: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"\n    [ERROR] Unexpected Pipeline Error: {exc}")
        sys.exit(1)

    # 5. Summary
    print("\n[3] Pipeline Execution Summary")
    print("-" * 60)
    print(f"    Status:         [OK] SUCCESS")
    print(f"    Artifact ID:    {processed_artifact.id}")
    print(f"    Parent Rec:     {processed_artifact.parent_recording_id}")
    print(f"    Meeting ID:     {processed_artifact.meeting_id}")
    print(f"    Output Path:    {processed_artifact.file_path}")
    print(f"    Duration:       {processed_artifact.duration_seconds:.2f} seconds")
    print(f"    Format/Codec:   {processed_artifact.format} / {processed_artifact.codec}")
    print(f"    Sample Rate:    {processed_artifact.sample_rate} Hz")
    print(f"    Channels:       {processed_artifact.channels}")
    print(f"    File Size:      {processed_artifact.file_size_bytes / 1024 / 1024:.2f} MB")
    print(f"    Processing T:   {processed_artifact.processing_duration_ms} ms")
    print("=" * 60)
    print("Future Pipeline Stages (STT, Extraction) will be appended here.")


if __name__ == "__main__":
    # Windows specific fix for asyncio if needed, but modern Python usually handles it.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nPipeline execution cancelled by user.")
        sys.exit(0)
