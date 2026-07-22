import logging
from typing import Dict, Tuple
from fastapi import HTTPException, status
import asyncpg.exceptions

logger = logging.getLogger(__name__)

TIMESHEET_ERROR_MAP: Dict[str, Tuple[int, str]] = {
    'EMPTY_TIMESHEET': (422, "Cannot submit an empty timesheet. Please add at least one time entry."),
    'SUBMISSION_DEADLINE_PASSED': (422, "The submission deadline for this timesheet has passed."),
    'NO_APPROVER_CONFIGURED': (202, "Timesheet submitted. Note: no approver is configured — a superadmin will be notified."),
    'ALREADY_SUBMITTED': (409, "This timesheet has already been submitted."),
    'DATE_OUT_OF_WEEK_RANGE': (422, "Entry date must fall within the timesheet's week."),
    'FUTURE_ENTRY_NOT_ALLOWED': (422, "Future date entries are not allowed by your organization's policy."),
    'PAST_ENTRY_NOT_ALLOWED': (422, "This date is beyond the allowed lookback window."),
    'OVERTIME_BLOCKED': (422, "This entry would exceed the maximum hours per day. Overtime entries are blocked by policy."),
    'INVALID_APPROVER_ROLE': (422, "The selected approver must be a Manager or Superadmin. Members cannot be assigned as approvers."),
    'BOARD_ORG_MISMATCH': (403, "The selected board does not belong to your organization."),
    'TIMESHEET_LOCKED': (422, "This timesheet is locked and cannot be modified after submission."),
    'TASK_NOT_ASSIGNED': (422, "Time can only be logged against tasks assigned to you."),
    'TASK_NOT_FOUND': (404, "The specified task was not found."),
    'TASK_LINK_REQUIRED': (422, "Task selection is required by your organization's timesheet policy."),
}


def handle_timesheet_db_error(exc: Exception):
    """
    Looks up stored procedure error codes in exception string and raises mapped HTTPException.
    Falls back to appropriate HTTP status codes for generic unauthorized, not found, or conflict errors.
    """
    err_str = str(exc)

    for code, (status_code, user_msg) in TIMESHEET_ERROR_MAP.items():
        if code in err_str:
            raise HTTPException(
                status_code=status_code,
                detail={"error_code": code, "detail": user_msg},
            )

    # General error handling fallbacks
    if "UNAUTHORIZED_APPROVER" in err_str or "UNAUTHORIZED" in err_str or "RECALL_DISABLED" in err_str or "Superadmin role required" in err_str or "Manager or Superadmin role required" in err_str:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=err_str,
        )
    elif "TIMESHEET_NOT_FOUND" in err_str or "ENTRY_NOT_FOUND" in err_str or "NOT_FOUND" in err_str:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=err_str,
        )
    elif "TIMESHEET_ALREADY_EXISTS" in err_str:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_code": "TIMESHEET_ALREADY_EXISTS", "detail": "Timesheet for this week already exists"},
        )
    else:
        logger.error(f"Database timesheet operation error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_str,
        )
