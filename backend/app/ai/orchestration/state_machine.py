from typing import Dict, List
from app.ai.schemas.planning import ExecutionStatus
from app.ai.exceptions import AIError, FailureCategory

class InvalidStateTransitionError(AIError):
    def __init__(self, from_state: str, to_state: str):
        message = f"Invalid state transition from {from_state} to {to_state}."
        super().__init__(message, category=FailureCategory.INFRASTRUCTURE_ERROR)

class ExecutionStateMachine:
    """
    Formal execution lifecycle state machine.
    Enforces valid transitions and prevents execution corruption.
    """
    
    # Define valid target states for each current state
    VALID_TRANSITIONS: Dict[ExecutionStatus, List[ExecutionStatus]] = {
        ExecutionStatus.CREATED: [
            ExecutionStatus.PLANNING,
            ExecutionStatus.WAITING_FOR_CONFIRMATION,
            ExecutionStatus.CANCELLED
        ],
        ExecutionStatus.PLANNING: [
            ExecutionStatus.VALIDATING,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED
        ],
        ExecutionStatus.VALIDATING: [
            ExecutionStatus.WAITING_FOR_CONFIRMATION,
            ExecutionStatus.EXECUTING,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED
        ],
        ExecutionStatus.WAITING_FOR_CONFIRMATION: [
            ExecutionStatus.VALIDATING,
            ExecutionStatus.EXECUTING,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.FAILED
        ],
        ExecutionStatus.EXECUTING: [
            ExecutionStatus.WAITING_FOR_CONFIRMATION,
            ExecutionStatus.COMPLETED,
            ExecutionStatus.PARTIALLY_COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED
        ],
        # Terminal states have no valid outward transitions
        ExecutionStatus.COMPLETED: [],
        ExecutionStatus.PARTIALLY_COMPLETED: [],
        ExecutionStatus.FAILED: [],
        ExecutionStatus.CANCELLED: [],
    }

    @classmethod
    def can_transition(cls, current_state: ExecutionStatus | str, new_state: ExecutionStatus | str) -> bool:
        if isinstance(current_state, str):
            current_state = ExecutionStatus(current_state)
        if isinstance(new_state, str):
            new_state = ExecutionStatus(new_state)
            
        return new_state in cls.VALID_TRANSITIONS.get(current_state, [])

    @classmethod
    def validate_transition(cls, current_state: ExecutionStatus | str, new_state: ExecutionStatus | str) -> None:
        """
        Validates the transition. Raises InvalidStateTransitionError if invalid.
        """
        if not cls.can_transition(current_state, new_state):
            c_val = current_state.value if isinstance(current_state, ExecutionStatus) else current_state
            n_val = new_state.value if isinstance(new_state, ExecutionStatus) else new_state
            raise InvalidStateTransitionError(c_val, n_val)
