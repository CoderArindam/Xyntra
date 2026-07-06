from enum import Enum
from typing import Dict, Any, Callable
from app.ai.exceptions import FailureCategory, AIError

class RecoveryAction(str, Enum):
    RETRY = "RETRY"              # Bounded backoff retry
    FAIL = "FAIL"                # Immediate failure
    CANCEL = "CANCEL"            # Graceful cancellation
    REPAIR = "REPAIR"            # Attempt prompt injection repair
    PARTIAL = "PARTIAL"          # Allow partial completion (e.g. tools)

class RecoveryPolicy:
    """
    Centralized recovery logic. Determines the appropriate action for a given failure category.
    """
    
    _policy_map: Dict[FailureCategory, RecoveryAction] = {
        FailureCategory.USER_ERROR: RecoveryAction.FAIL,
        FailureCategory.VALIDATION_ERROR: RecoveryAction.FAIL,
        FailureCategory.PERMISSION_ERROR: RecoveryAction.FAIL,
        FailureCategory.AI_PROVIDER_ERROR: RecoveryAction.FAIL,
        FailureCategory.PARSING_ERROR: RecoveryAction.REPAIR,
        FailureCategory.INFRASTRUCTURE_ERROR: RecoveryAction.FAIL,
        FailureCategory.BUSINESS_LOGIC_ERROR: RecoveryAction.PARTIAL,
        FailureCategory.TEMPORARY_FAILURE: RecoveryAction.RETRY,
        FailureCategory.PERMANENT_FAILURE: RecoveryAction.FAIL,
    }

    @classmethod
    def get_action(cls, category: FailureCategory) -> RecoveryAction:
        return cls._policy_map.get(category, RecoveryAction.FAIL)

    @classmethod
    def determine_action_for_error(cls, error: Exception) -> RecoveryAction:
        if isinstance(error, AIError):
            return cls.get_action(error.category)
        return RecoveryAction.FAIL
