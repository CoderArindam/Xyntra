"""Discover latest meeting and process it through the End-to-End Orchestrator."""

import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.meeting.config import meeting_config

def get_latest_meeting_id() -> str:
    """Find the most recently modified session directory."""
    processing_dir = Path(meeting_config.PROCESSING_OUTPUT_DIR)
    recordings_dir = Path(meeting_config.RECORDING_OUTPUT_DIR)
    
    candidates = []
    if processing_dir.exists():
        candidates.extend([d for d in processing_dir.iterdir() if d.is_dir()])
    if recordings_dir.exists():
        candidates.extend([d for d in recordings_dir.iterdir() if d.is_dir()])
        
    if not candidates:
        print("[ERROR] No meetings found.")
        sys.exit(1)
        
    latest_dir = max(candidates, key=lambda d: d.stat().st_mtime)
    return latest_dir.name


async def main() -> None:
    latest_id = get_latest_meeting_id()
    
    # We just delegate to process_meeting.py by importing and running its orchestrator logic
    # but since it's a CLI tool, we can just run the orchestrator here directly.
    from app.meeting.pipeline.orchestrator import MeetingPipelineOrchestrator
    
    print("=================================================")
    print("KAIO Meeting Processing Pipeline (Latest)")
    print("=================================================\n")
    
    print(f"Meeting: {latest_id}\n")

    orchestrator = MeetingPipelineOrchestrator(meeting_id=latest_id)
    success = await orchestrator.execute_pipeline()
    
    # Print Console Summary
    for timing in orchestrator.stage_timings:
        status = timing["status"]
        name = timing["stage_name"].replace("Stage", "")
        if status == "SUCCESS":
            print(f"✓ {name} Complete ({timing['duration_ms']} ms)")
        elif status == "SKIPPED":
            print(f"⏭ {name} Skipped")
        else:
            print(f"✗ {name} Failed: {timing.get('error')}")

    print("\n-------------------------------------")
    if success:
        print("Pipeline Completed")
    else:
        print("Pipeline Failed")
        
    print(f"\nMeeting ID: {latest_id}")
    
    if orchestrator.context.completed_at:
        print(f"Processing Time: {sum(s['duration_ms'] for s in orchestrator.stage_timings)} ms")
        
    print("\nArtifacts Generated:")
    for stage in orchestrator.stages:
        for art in stage.generated_artifacts:
            print(f"  - {art.__name__}")
            
    print(f"\nFinal Transcript: participant_attributed_transcript.json")
    print(f"Report: pipeline_report.json")
    print("=================================================")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
