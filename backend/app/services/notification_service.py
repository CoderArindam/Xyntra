from app.services.email_service import send_email
from app.services.email_templates import (
    task_assigned_template,
    task_assignment_changed_template,
    task_status_changed_template,
    task_comment_added_template
)
import logging

logger = logging.getLogger(__name__)

def dispatch_task_email(
    activity_type: str,
    task_title: str,
    board_name: str,
    actor_name: str,
    assignee_email: str = None,
    assignee_name: str = None,
    old_assignee_email: str = None,
    old_assignee_name: str = None,
    old_status: str = None,
    new_status: str = None,
    comment: str = None
):
    """
    Dispatches appropriate emails based on the activity.
    Should be called via FastAPI BackgroundTasks so it doesn't block the API.
    """
    try:
        if activity_type == "ASSIGNEE_CHANGED":
            if assignee_email:
                subject = "You have been assigned a task"
                body = task_assigned_template(task_title, board_name, actor_name)
                send_email(assignee_email, subject, body)
                
            if old_assignee_email and old_assignee_email != assignee_email:
                subject = "Task assignment updated"
                body = task_assignment_changed_template(task_title, assignee_name or assignee_email)
                send_email(old_assignee_email, subject, body)

        elif activity_type == "STATUS_CHANGED":
            if assignee_email:
                subject = f"Task status updated to {new_status}"
                body = task_status_changed_template(task_title, old_status, new_status, actor_name)
                send_email(assignee_email, subject, body)
                
        elif activity_type == "DUE_DATE_CHANGED":
            if assignee_email:
                subject = "Task due date updated"
                # using assignment changed template as a fallback since no specific template exists for due dates,
                # but standard practice is just reuse a generic update or create one.
                # Actually, let's just send a simple text email if there's no template
                body = f"Hi {assignee_name or 'there'},\n\nThe due date for the task '{task_title}' was updated by {actor_name}.\n\nThanks,\nThe Team"
                send_email(assignee_email, subject, body)

        elif activity_type == "COMMENT_ADDED":
            if assignee_email:
                subject = "New comment on your task"
                body = task_comment_added_template(task_title, actor_name, comment or "")
                send_email(assignee_email, subject, body)

    except Exception as e:
        logger.error(f"Failed to dispatch email notification for {activity_type}: {e}")

