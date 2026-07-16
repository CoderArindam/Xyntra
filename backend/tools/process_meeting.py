"""Process a specific meeting session through the End-to-End Orchestrator."""

import argparse
import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.meeting.pipeline.orchestrator import MeetingPipelineOrchestrator


async def main() -> None:
    parser = argparse.ArgumentParser(description="Process a specific meeting through the pipeline.")
    parser.add_argument("--meeting-id", required=True, help="The Meeting ID to process")
    args = parser.parse_args()

    print("=================================================")
    print("KAIO Meeting Processing Pipeline")
    print("=================================================\n")
    
    print(f"Meeting: {args.meeting_id}\n")

    orchestrator = MeetingPipelineOrchestrator(meeting_id=args.meeting_id)
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
        
    print(f"\nMeeting ID: {args.meeting_id}")
    
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
