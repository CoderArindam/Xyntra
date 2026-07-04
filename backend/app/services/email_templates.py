def task_assigned_template(
    task_title: str,
    board_name: str,
    assigned_by_name: str
) -> str:

    return f"""
Hi there 👋


You have been assigned a new task.


━━━━━━━━━━━━━━━━━━━━━━

📌 Task

{task_title}


📂 Board

{board_name}


👤 Assigned by

{assigned_by_name}

━━━━━━━━━━━━━━━━━━━━━━



It's time to get started.

Open your workspace to view the task details, collaborate with your team, and keep the project moving forward.



👉 Next steps:

• Review the task requirements
• Add updates or comments
• Mark progress as you complete the work



Thanks,

The Team
"""





def task_assignment_changed_template(
    task_title: str,
    assigned_user_name: str
) -> str:

    return f"""
Hi there 👋


A task assignment has been updated.


━━━━━━━━━━━━━━━━━━━━━━

📌 Task

{task_title}


👤 New Assignee

{assigned_user_name}

━━━━━━━━━━━━━━━━━━━━━━



The ownership of this task has changed successfully.



You can open your workspace to see the latest updates and continue collaborating with your team.



Thanks,

The Team
"""





def task_status_changed_template(
    task_title: str,
    old_status: str,
    new_status: str,
    changed_by_name: str
) -> str:

    return f"""
Hi there 👋


A task status update was made.


━━━━━━━━━━━━━━━━━━━━━━

📌 Task

{task_title}


🔄 Status Changed

{old_status}

↓

{new_status}


👤 Updated by

{changed_by_name}

━━━━━━━━━━━━━━━━━━━━━━



Your project activity has been updated.

Visit your workspace to review the latest progress.



Thanks,

The Team
"""





def task_comment_added_template(
    task_title: str,
    commenter_name: str,
    comment: str
) -> str:

    return f"""
Hi there 👋


Someone added a new comment to a task you follow.


━━━━━━━━━━━━━━━━━━━━━━

📌 Task

{task_title}


💬 Comment by

{commenter_name}



"{comment}"

━━━━━━━━━━━━━━━━━━━━━━



Open your workspace to reply and continue the discussion.



Thanks,

The Team
"""