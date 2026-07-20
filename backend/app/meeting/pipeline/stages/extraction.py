"""Stage 7: Task Extraction Stage."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Type, Optional

from app.meeting.artifacts.base import MeetingArtifact
from app.meeting.artifacts.speaker import ParticipantAttributedTranscript, ParticipantRoster
from app.meeting.artifacts.task import ExtractedTask
from app.meeting.pipeline.context import PipelineContext
from app.meeting.pipeline.stage import PipelineStage, StageStatus
from app.meeting.providers.extraction.llm_task_extractor import LLMTaskExtractor
from app.meeting.config import meeting_config
from app.database.connection import db

logger = logging.getLogger("meeting.pipeline.stages.extraction")


class TaskExtractionStage(PipelineStage):
    """Extracts candidate task proposals from finalized attributed transcripts via LLM."""

    @property
    def stage_name(self) -> str:
        return "TaskExtractionStage"

    @property
    def execution_order(self) -> int:
        return 1000

    @property
    def required_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [ParticipantAttributedTranscript]

    @property
    def generated_artifacts(self) -> List[Type[MeetingArtifact]]:
        return []

    @property
    def retryable(self) -> bool:
        return False

    @property
    def continue_on_failure(self) -> bool:
        return True

    async def execute(self, context: PipelineContext) -> StageStatus:
        transcript = context.artifacts.get(ParticipantAttributedTranscript)
        roster = context.artifacts.get(ParticipantRoster)

        if not transcript or not transcript.segments:
            logger.warning("No ParticipantAttributedTranscript available for TaskExtractionStage.")
            self._write_manifest(context.session_directory, context.meeting_id, "extraction_failed", 0, "Missing attributed transcript artifact.")
            return StageStatus.SUCCESS

        # Task 1: Check transcript word count threshold before invoking LLM
        total_words = sum(len(seg.text.split()) for seg in transcript.segments if seg.text)
        min_words = getattr(meeting_config, "EXTRACTION_MIN_TRANSCRIPT_WORDS", 20)

        if total_words < min_words:
            logger.info(
                f"Skipping task extraction for meeting '{context.meeting_id}': "
                f"total transcript words ({total_words}) is below threshold ({min_words})."
            )
            self._write_manifest(
                context.session_directory,
                context.meeting_id,
                "skipped_insufficient_content",
                0,
                error=f"Total words ({total_words}) below minimum threshold ({min_words})"
            )
            return StageStatus.SUCCESS

        extractor = LLMTaskExtractor()

        try:
            org_id = context.metadata.get("org_id", 1)
            meeting_session_id = context.meeting_id

            # Task 1: Fetch org's active boards and users via DB pool
            boards = []
            org_users = []
            if db.pool is None:
                await db.connect()

            if db.pool:
                async with db.pool.acquire() as conn:
                    rows = await conn.fetch(
                        "SELECT id, name FROM boards WHERE organization_id = $1 AND archived_at IS NULL",
                        org_id
                    )
                    boards = [{"id": r["id"], "name": r["name"]} for r in rows]

                    user_rows = await conn.fetch(
                        "SELECT id, first_name, last_name, email FROM users WHERE organization_id = $1 AND deleted_at IS NULL",
                        org_id
                    )
                    org_users = [dict(r) for r in user_rows]

            extracted_tasks: List[ExtractedTask] = await extractor.extract(transcript, roster, boards=boards, users=org_users)
            logger.info(f"LLMTaskExtractor extracted {len(extracted_tasks)} candidate proposals.")

            created_proposals = []

            # Persist proposals into database using fn_create_task_proposal
            if extracted_tasks:
                async with db.pool.acquire() as conn:
                    # Ensure meeting_session exists in meeting_sessions table
                    await conn.execute(
                        """
                        INSERT INTO meeting_sessions (id, session_id, org_id, status)
                        VALUES ($1::uuid, $2, $3::integer, 'completed')
                        ON CONFLICT (id) DO NOTHING
                        """,
                        meeting_session_id,
                        meeting_session_id,
                        org_id
                    )

                    for task in extracted_tasks:
                        try:
                            due_date_val = None
                            if getattr(task, "due_date", None):
                                try:
                                    due_date_val = datetime.fromisoformat(str(task.due_date).replace("Z", "+00:00"))
                                except Exception:
                                    due_date_val = None

                            target_board_id = task.suggested_board_id or context.metadata.get("board_id")

                            proposal_row = await conn.fetchrow(
                                """
                                SELECT * FROM fn_create_task_proposal(
                                    $1::integer,
                                    $2::integer,
                                    $3::uuid,
                                    $4::text,
                                    $5::text,
                                    $6::integer,
                                    $7::numeric,
                                    $8::text,
                                    $9::jsonb,
                                    $10::numeric,
                                    $11::board_resolution_source,
                                    $12::text,
                                    $13::timestamptz
                                )
                                """,
                                org_id,
                                target_board_id,
                                meeting_session_id,
                                task.title,
                                task.description,
                                task.suggested_assignee_id,
                                task.confidence_score,
                                task.source_transcript_quote,
                                json.dumps(task.raw_llm_payload or {}),
                                task.board_confidence,
                                task.board_source,
                                getattr(task, "priority", "MEDIUM"),
                                due_date_val
                            )
                            if proposal_row:
                                created_proposals.append(dict(proposal_row))
                        except Exception as db_err:
                            logger.error(f"Failed to persist task proposal '{task.title}': {db_err}")


            self._write_manifest(
                context.session_directory,
                context.meeting_id,
                "completed",
                len(created_proposals),
                proposals=created_proposals
            )
            return StageStatus.SUCCESS

        except Exception as e:
            error_msg = f"Task extraction failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            context.warnings.append(error_msg)
            self._write_manifest(
                context.session_directory,
                context.meeting_id,
                "extraction_failed",
                0,
                error=error_msg
            )
            return StageStatus.SUCCESS

    def _write_manifest(
        self,
        session_dir: Path,
        meeting_id: str,
        status: str,
        proposals_count: int,
        error: Optional[str] = None,
        proposals: Optional[List[dict]] = None
    ) -> None:
        """Writes task_proposals_manifest.json to session output directory."""
        manifest = {
            "meeting_id": meeting_id,
            "status": status,
            "proposals_count": proposals_count,
            "extracted_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "error": error,
            "proposals": proposals or []
        }
        manifest_path = session_dir / "task_proposals_manifest.json"
        session_dir.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
