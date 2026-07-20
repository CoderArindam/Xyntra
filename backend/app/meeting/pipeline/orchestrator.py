"""Master pipeline orchestrator."""

import time
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.meeting.config import meeting_config
from app.meeting.logger import get_logger
from app.meeting.pipeline.context import PipelineContext, ArtifactRegistry
from app.meeting.pipeline.events import (
    PipelineStarted, PipelineCompleted, StageStarted, StageCompleted, 
    StageSkipped, StageFailed
)
from app.meeting.pipeline.stage import PipelineStage, StageStatus
from app.meeting.pipeline.stages import ALL_STAGES

# Import artifacts used for discovery
from app.meeting.artifacts.recording import MeetingRecording

log = get_logger("pipeline.orchestrator")


class MeetingPipelineOrchestrator:
    """End-to-End Orchestrator for Meeting Intelligence."""

    def __init__(self, meeting_id: str, metadata: Dict[str, Any] = None):
        self.meeting_id = meeting_id
        
        # Determine base directory for this meeting session
        # We prefer the processing directory, but fallback to recordings if needed
        self.session_dir = Path(meeting_config.PROCESSING_OUTPUT_DIR) / meeting_id
        if not self.session_dir.exists():
            self.session_dir.mkdir(parents=True, exist_ok=True)
            
        meta = metadata or {}
        self.context = PipelineContext(
            meeting_id=meeting_id,
            session_directory=self.session_dir,
            artifacts=ArtifactRegistry(self.session_dir),
            metadata=meta
        )
        
        # Sort stages by explicit execution order
        self.stages: List[PipelineStage] = sorted(ALL_STAGES, key=lambda s: s.execution_order)
        
        # For the manifest
        self.stage_timings: List[Dict[str, Any]] = []

    def _ensure_initial_recording(self) -> None:
        """Helper to create a MeetingRecording artifact if we only have the raw recording file."""
        if self.context.artifacts.exists(MeetingRecording):
            return
            
        # Look for the raw recording in the RECORDING_OUTPUT_DIR
        raw_audio_dir = Path(meeting_config.RECORDING_OUTPUT_DIR) / self.meeting_id
        if not raw_audio_dir.exists():
            return
            
        media_extensions = ['.wav', '.webm', '.mp4', '.mkv', '.ogg']
        recording_file = None
        
        # Prioritize recording.wav for backward compatibility
        if (raw_audio_dir / "recording.wav").exists():
            recording_file = raw_audio_dir / "recording.wav"
        else:
            for f in raw_audio_dir.iterdir():
                if f.is_file() and f.suffix.lower() in media_extensions:
                    recording_file = f
                    break
        
        if recording_file:
            ext = recording_file.suffix.lower().lstrip('.')
            mime = f"audio/{ext}" if ext in ['wav', 'ogg'] else f"video/{ext}"
            codec = "pcm_s16le" if ext == "wav" else "unknown"
            
            now_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            
            # Calculate actual sha256 checksum
            hasher = hashlib.sha256()
            with open(recording_file, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            checksum = hasher.hexdigest()
            
            recording = MeetingRecording(
                meeting_id=self.meeting_id,
                file_path=str(recording_file),
                storage_uri=recording_file.resolve().as_uri(),
                duration_seconds=300.0,
                format=ext,
                sample_rate=16000,
                channel_count=1,
                codec=codec,
                mime_type=mime,
                file_size_bytes=recording_file.stat().st_size,
                checksum_sha256=checksum,
                recording_start_time=now_str,
                recording_end_time=now_str,
                recording_status="completed"
            )
            # Register it in our PROCESSING directory registry so it cascades
            self.context.artifacts.register(recording)

    def _emit(self, event: Any) -> None:
        """Emit pipeline event."""
        self.context.events.append(event)
        
        if isinstance(event, StageStarted):
            log.info("pipeline.stage.started", stage=event.stage_name)
        elif isinstance(event, StageCompleted):
            log.info("pipeline.stage.completed", stage=event.stage_name, duration_ms=event.duration_ms)
        elif isinstance(event, StageSkipped):
            log.info("pipeline.stage.skipped", stage=event.stage_name, reason=event.reason)
        elif isinstance(event, StageFailed):
            log.error("pipeline.stage.failed", stage=event.stage_name, error=event.error)

    def _generate_manifest(self) -> None:
        """Write the audit log manifest."""
        manifest = {
            "meeting_id": self.context.meeting_id,
            "pipeline_version": self.context.processing_version,
            "started_at": self.context.started_at,
            "completed_at": self.context.completed_at,
            "stages": self.stage_timings,
            "completed_stages": self.context.completed_stages,
            "skipped_stages": self.context.skipped_stages,
            "failed_stage": self.context.failed_stage,
            "warnings": self.context.warnings,
            "diagnostics": self.context.diagnostics
        }
        
        manifest_path = self.context.session_directory / "pipeline_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def _generate_report(self) -> None:
        """Write a high level business report."""
        from app.meeting.artifacts.speaker import ParticipantAttributedTranscript, SpeakerMapping
        from app.meeting.artifacts.transcript import NormalizedTranscript
        
        report = {
            "meeting_id": self.context.meeting_id,
            "pipeline_runtime_ms": 0,
            "transcript_segments": 0,
            "resolved_speakers": 0,
            "unresolved_speakers": 0,
            "warnings": self.context.warnings
        }
        
        if self.context.completed_at:
            t0 = datetime.fromisoformat(self.context.started_at.replace("Z", ""))
            t1 = datetime.fromisoformat(self.context.completed_at.replace("Z", ""))
            report["pipeline_runtime_ms"] = int((t1 - t0).total_seconds() * 1000)
            
        norm_ts = self.context.artifacts.get(NormalizedTranscript)
        if norm_ts:
            report["transcript_segments"] = len(norm_ts.segments)
            
        mapping = self.context.artifacts.get(SpeakerMapping)
        if mapping:
            report["resolved_speakers"] = mapping.resolved_count
            report["unresolved_speakers"] = mapping.unresolved_count

        report_path = self.context.session_directory / "pipeline_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    async def execute_pipeline(self) -> bool:
        """Run the full pipeline."""
        self._emit(PipelineStarted(meeting_id=self.meeting_id))
        
        # Setup initial state
        self._ensure_initial_recording()
        
        pipeline_success = True
        
        for stage in self.stages:
            stage_info = {
                "stage_name": stage.stage_name,
                "execution_order": stage.execution_order,
                "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "completed_at": None,
                "duration_ms": 0,
                "status": None,
                "error": None,
                "retry_count": 0
            }
            
            # Check if we can skip (resumability)
            can_skip = stage.skippable
            if can_skip:
                for gen_art in stage.generated_artifacts:
                    if not self.context.artifacts.exists(gen_art):
                        can_skip = False
                        break
                    
            if can_skip and stage.generated_artifacts:
                stage_info["status"] = StageStatus.SKIPPED.value
                self.stage_timings.append(stage_info)
                self.context.skipped_stages.append(stage.stage_name)
                self._emit(StageSkipped(meeting_id=self.meeting_id, stage_name=stage.stage_name))
                continue

            self._emit(StageStarted(meeting_id=self.meeting_id, stage_name=stage.stage_name))
            
            # Validate inputs
            try:
                stage.validate_inputs(self.context)
            except Exception as e:
                stage_info["status"] = StageStatus.FAILED.value
                stage_info["error"] = f"Input validation failed: {str(e)}"
                self.stage_timings.append(stage_info)
                self.context.failed_stage = stage.stage_name
                self._emit(StageFailed(
                    meeting_id=self.meeting_id, 
                    stage_name=stage.stage_name, 
                    error=stage_info["error"], 
                    will_continue=False
                ))
                pipeline_success = False
                break
                
            # Execute
            t0 = time.monotonic()
            retries = 1 if stage.retryable else 0
            status = StageStatus.FAILED
            
            for attempt in range(retries + 1):
                try:
                    status = await stage.execute(self.context)
                    if status == StageStatus.SUCCESS:
                        break
                except Exception as e:
                    stage_info["error"] = str(e)
                    if attempt < retries:
                        stage_info["retry_count"] += 1
                        time.sleep(1) # simple backoff
                        
            # Validate outputs
            if status == StageStatus.SUCCESS:
                try:
                    stage.validate_outputs(self.context)
                except Exception as e:
                    status = StageStatus.FAILED
                    stage_info["error"] = f"Output validation failed: {str(e)}"

            duration = int((time.monotonic() - t0) * 1000)
            stage_info["completed_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            stage_info["duration_ms"] = duration
            stage_info["status"] = status.value
            self.stage_timings.append(stage_info)
            
            if status == StageStatus.SUCCESS:
                self.context.completed_stages.append(stage.stage_name)
                
                # Capture hashes/versions of outputs
                generated_info = {}
                for art_type in stage.generated_artifacts:
                    art = self.context.artifacts.get(art_type)
                    if art:
                        generated_info[art_type.__name__] = getattr(art, "id", "unknown")
                        
                self._emit(StageCompleted(
                    meeting_id=self.meeting_id, 
                    stage_name=stage.stage_name, 
                    duration_ms=duration,
                    generated_artifacts=generated_info
                ))
            else:
                self.context.failed_stage = stage.stage_name
                self._emit(StageFailed(
                    meeting_id=self.meeting_id, 
                    stage_name=stage.stage_name, 
                    error=stage_info["error"] or "Stage returned FAILED", 
                    will_continue=stage.continue_on_failure
                ))
                
                if not stage.continue_on_failure:
                    pipeline_success = False
                    break
                    
        self.context.completed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        if pipeline_success:
            self._emit(PipelineCompleted(
                meeting_id=self.meeting_id, 
                total_duration_ms=sum(s["duration_ms"] for s in self.stage_timings)
            ))
            
        self._generate_manifest()
        self._generate_report()
        
        return pipeline_success
