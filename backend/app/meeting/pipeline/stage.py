"""Base definitions for pipeline stages."""

from enum import Enum
from abc import ABC, abstractmethod
from typing import List, Type

from app.meeting.artifacts.base import MeetingArtifact
from app.meeting.pipeline.context import PipelineContext


class StageStatus(str, Enum):
    """Execution status of a pipeline stage."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    PARTIAL = "PARTIAL"


class PipelineStage(ABC):
    """Abstract interface for a stage in the meeting processing pipeline."""
    
    @property
    @abstractmethod
    def stage_name(self) -> str:
        """Name of the stage."""
        pass
        
    @property
    @abstractmethod
    def execution_order(self) -> int:
        """Order of execution. Lower executes first."""
        pass
        
    @property
    @abstractmethod
    def required_artifacts(self) -> List[Type[MeetingArtifact]]:
        """Artifacts that must be present in context before execution."""
        pass
        
    @property
    @abstractmethod
    def generated_artifacts(self) -> List[Type[MeetingArtifact]]:
        """Artifacts guaranteed to be produced by this stage."""
        pass
        
    @property
    def retryable(self) -> bool:
        """Whether this stage can be retried on failure."""
        return False
        
    @property
    def continue_on_failure(self) -> bool:
        """Whether the pipeline should continue if this stage fails."""
        return False

    @property
    def skippable(self) -> bool:
        """Whether this stage can be skipped if its outputs already exist."""
        return True

    def validate_inputs(self, context: PipelineContext) -> None:
        """Ensure all required inputs exist."""
        missing = []
        for required_type in self.required_artifacts:
            if not context.artifacts.exists(required_type):
                missing.append(required_type.__name__)
                
        if missing:
            raise ValueError(f"Stage '{self.stage_name}' missing required artifacts: {missing}")

    def validate_outputs(self, context: PipelineContext) -> None:
        """Ensure all expected outputs were generated."""
        missing = []
        for generated_type in self.generated_artifacts:
            if not context.artifacts.exists(generated_type):
                missing.append(generated_type.__name__)
                
        if missing:
            raise ValueError(f"Stage '{self.stage_name}' failed to generate artifacts: {missing}")

    @abstractmethod
    async def execute(self, context: PipelineContext) -> StageStatus:
        """Run the business logic of this stage."""
        pass
