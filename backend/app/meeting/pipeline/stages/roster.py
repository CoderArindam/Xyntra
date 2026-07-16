"""Participant Roster Stage."""

from typing import List, Type

from app.meeting.artifacts.base import MeetingArtifact
from app.meeting.artifacts.speaker import ParticipantPresenceTimeline, ParticipantRoster
from app.meeting.pipeline.context import PipelineContext
from app.meeting.pipeline.stage import PipelineStage, StageStatus
from app.meeting.providers.participant_presence.roster_builder import ParticipantRosterBuilder

class ParticipantRosterStage(PipelineStage):
    """Reduces the presence timeline into a canonical participant roster."""

    @property
    def stage_name(self) -> str:
        return "ParticipantRosterStage"

    @property
    def execution_order(self) -> int:
        return 700

    @property
    def required_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [ParticipantPresenceTimeline]

    @property
    def generated_artifacts(self) -> List[Type[MeetingArtifact]]:
        return [ParticipantRoster]

    @property
    def retryable(self) -> bool:
        return False

    @property
    def continue_on_failure(self) -> bool:
        return False

    async def execute(self, context: PipelineContext) -> StageStatus:
        timeline = context.artifacts.get(ParticipantPresenceTimeline)
        if not timeline:
            return StageStatus.FAILED
            
        builder = ParticipantRosterBuilder()
        
        try:
            roster = builder.build(timeline)
            if not roster or not roster.participants:
                context.warnings.append("Roster building failed: empty roster")
                return StageStatus.FAILED
                
            context.artifacts.register(roster)
            return StageStatus.SUCCESS
        except Exception as e:
            context.warnings.append(f"Roster building failed: {str(e)}")
            return StageStatus.FAILED
