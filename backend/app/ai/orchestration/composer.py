import json
from typing import Dict, Any, AsyncGenerator, Callable
from app.ai.schemas.planning import ExecutionResult, ExecutionContext, ExecutionStatus
from app.ai.gateway.ai_gateway import AIGateway
from app.ai.prompts.registry import PromptRegistry

from app.ai.orchestration.renderers import render_list, render_entity, render_success, render_failure


class TemplateRegistry:
    def __init__(self):
        self.templates: Dict[str, Callable[[Any], str | None]] = {}
        
    def register(self, action_name: str, handler: Callable[[Any], str | None]):
        self.templates[action_name] = handler
        
    def get_template(self, result: ExecutionResult) -> str | None:
        if result.status == ExecutionStatus.FAILED:
            # Extract error details from step results
            errors = [sr.error for sr in result.step_results if sr.error]
            if errors:
                return f"I ran into an issue: {errors[0]}"
            return "I encountered an error while trying to complete that request."
            
        if not hasattr(result, "step_results") or not result.step_results:
            return None
            
        parts = []
        for step_res in result.step_results:
            action_name = step_res.action
            if action_name in self.templates:
                rendered = self.templates[action_name](step_res.output)
                if rendered:
                    parts.append(rendered)
            elif step_res.tool_name in self.templates:
                rendered = self.templates[step_res.tool_name](step_res.output)
                if rendered:
                    parts.append(rendered)
                    
        # Filter out empty list messages ("You don't have any...") if there's already a successful mutation
        final_parts = []
        has_mutation = any("successfully" in p.lower() or "added" in p.lower() or "created" in p.lower() or "deleted" in p.lower() for p in parts)
        for p in parts:
            if has_mutation and ("you don't have any" in p.lower() or "no tasks found" in p.lower() or "no comments found" in p.lower()):
                continue
            final_parts.append(p)
            
        if final_parts:
            return "\n\n".join(final_parts)
            
        return None


template_registry = TemplateRegistry()


# --- Workspace Read Templates ---

def _render_projects(output):
    if not output or not isinstance(output, dict):
        return None
    projects = output.get("projects", [])
    if not projects:
        return "You don't have any projects yet. Would you like me to create one?"
    return render_list(
        f"You have **{len(projects)}** project{'s' if len(projects) != 1 else ''}:",
        projects,
        display_field="name"
    )

template_registry.register("list_projects", _render_projects)
template_registry.register("list_boards", _render_projects)


def _render_tasks(output):
    if not output or not isinstance(output, dict):
        return None
    tasks = output.get("tasks", [])
    if not tasks:
        return "No tasks found matching your criteria."
    count = len(tasks)
    return render_list(
        f"Found **{count}** task{'s' if count != 1 else ''}:",
        tasks,
        display_field="title",
        secondary_field="column_name"
    )

template_registry.register("list_tasks", _render_tasks)


def _render_users(output):
    if not output or not isinstance(output, dict):
        return None
    users = output.get("users", [])
    if not users:
        return "No workspace members found."
    return render_list(
        f"**{len(users)}** workspace member{'s' if len(users) != 1 else ''}:",
        users,
        display_field="first_name",
        secondary_field="email"
    )

template_registry.register("get_users", _render_users)


def _render_task_details(output):
    if not output or not isinstance(output, dict):
        return None
    return render_entity(
        "Task Details",
        output.get("task", {}),
        fields=["title", "column_name", "priority", "assignee_id", "due_date", "description"]
    )

template_registry.register("get_task_details", _render_task_details)


def _render_board_summary(output):
    if not output or not isinstance(output, dict):
        return None
    total = output.get("total_tasks", 0)
    completed = output.get("completed_tasks", 0)
    progress = output.get("progress_percent", 0)
    overdue = output.get("overdue_tasks", 0)
    by_status = output.get("tasks_by_status", {})
    members = output.get("member_count", 0)
    
    lines = [f"### Project Summary\n"]
    lines.append(f"- **Total Tasks:** {total}")
    lines.append(f"- **Progress:** {progress}% complete ({completed}/{total})")
    if overdue > 0:
        lines.append(f"- ⚠️ **Overdue:** {overdue} task{'s' if overdue != 1 else ''}")
    lines.append(f"- **Members:** {members}")
    
    if by_status:
        lines.append(f"\n**By Status:**")
        for status, count in by_status.items():
            lines.append(f"- {status}: {count}")
    
    by_priority = output.get("tasks_by_priority", {})
    if by_priority:
        lines.append(f"\n**By Priority:**")
        for prio, count in by_priority.items():
            lines.append(f"- {prio}: {count}")
    
    return "\n".join(lines)

template_registry.register("get_board_summary", _render_board_summary)


# --- Mutation Templates ---

def _render_create_task(output):
    if not output or not isinstance(output, dict):
        return None
    msg = output.get("message", "Task created successfully")
    return render_success("Task Created", msg)

template_registry.register("create_task", _render_create_task)


def _render_update_task(output):
    if not output or not isinstance(output, dict):
        return None
    action = output.get("action", "updated")
    title = f"Task {action.replace('_', ' ').title()}"
    msg = output.get("message", "Task updated successfully")
    return render_success(title, msg)

template_registry.register("update_task", _render_update_task)


def _render_delete_task(output):
    if not output or not isinstance(output, dict):
        return None
    return render_success("Task Deleted", output.get("message", "Task deleted successfully"))

template_registry.register("delete_task", _render_delete_task)


def _render_create_board(output):
    if not output or not isinstance(output, dict):
        return None
    return render_success("Project Created", output.get("message", "Project created successfully"))

template_registry.register("create_board", _render_create_board)


def _render_archive_board(output):
    if not output or not isinstance(output, dict):
        return None
    return render_success("Project Archived", output.get("message", "Project archived successfully"))

template_registry.register("archive_board", _render_archive_board)


def _render_delete_board(output):
    if not output or not isinstance(output, dict):
        return None
    return render_success("Project Deleted", output.get("message", "Project deleted successfully"))

template_registry.register("delete_board", _render_delete_board)


def _render_add_comment(output):
    if not output or not isinstance(output, dict):
        return None
    return render_success("Comment Added", output.get("message", "Comment added successfully"))

template_registry.register("add_comment", _render_add_comment)


def _render_get_comments(output):
    if not output or not isinstance(output, dict):
        return None
    verified = output.get("verified", {})
    comments = verified.get("comments", [])
    if not comments:
        return "No comments found for this task."
    
    lines = [f"Found **{len(comments)}** comment{'s' if len(comments) != 1 else ''}:"]
    for c in comments:
        user_name = f"{c.get('user_first_name') or ''} {c.get('user_last_name') or ''}".strip() or "User"
        date = c.get('created_at', '').split('T')[0] if c.get('created_at') else ""
        content = c.get('content', '')
        lines.append(f"**{user_name}** ({date}):\n> {content}")
        
    return "\n\n".join(lines)

template_registry.register("get_comments", _render_get_comments)

# --- Profile and Appearance Templates ---

def _render_update_profile(output):
    if not output or not isinstance(output, dict):
        return None
    msg = output.get("message", "Profile updated successfully.")
    return render_success("Profile Updated", msg)

template_registry.register("update_profile", _render_update_profile)

def _render_get_my_profile(output):
    if not output or not isinstance(output, dict):
        return None
    return render_entity(
        "Your Profile",
        output.get("verified", {}),
        fields=["first_name", "last_name", "email"]
    )

template_registry.register("get_my_profile", _render_get_my_profile)

def _render_update_appearance(output):
    if not output or not isinstance(output, dict):
        return None
    msg = output.get("message", "Appearance preferences updated.")
    return render_success("Appearance Updated", msg)

template_registry.register("update_appearance", _render_update_appearance)

def _render_get_my_appearance(output):
    if not output or not isinstance(output, dict):
        return None
    return render_entity(
        "Appearance Preferences",
        output.get("verified", {}),
        fields=["theme", "accent_color", "sidebar_theme", "sidebar_collapsed"]
    )

template_registry.register("get_my_appearance", _render_get_my_appearance)



# --- Composer ---

class ResponseComposer:
    """
    Transforms an ExecutionResult into a user-friendly conversational response.
    Uses deterministic templates where possible to save tokens and latency,
    falling back to the LLM for complex summaries.
    """
    
    def __init__(self, gateway: AIGateway):
        self.gateway = gateway
        
    async def compose(self, result: ExecutionResult, context: ExecutionContext) -> AsyncGenerator[str, None]:
        from app.ai.telemetry.context import Span
        
        with Span("Compose Response", "ResponseComposer") as span:
            yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_start', 'execution_id': context.execution_id})}\n\n"
            
            template_response = template_registry.get_template(result)
            
            if template_response:
                span.metadata["method"] = "template"
                yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_chunk', 'content': template_response})}\n\n"
            else:
                span.metadata["method"] = "llm"
                system_prompt = PromptRegistry.render_prompt(
                    agent_name="workspace_assistant",
                    prompt_name="composer",
                    context={},
                    version="v1"
                )
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Please summarize this execution result:\n\n{result.model_dump_json()}"}
                ]
                
                stream_gen = self.gateway.stream_prompt(
                    messages=messages,
                    org_ai_enabled=True,
                    user_has_permission=context.current_user.get("role") in ["SUPER_ADMIN", "MANAGER"],
                    workflow_id="response_composition",
                    request_id=context.request_id,
                    organization_id=context.organization_id,
                    user_id=str(context.current_user.get("id"))
                )
                
                async for chunk in stream_gen:
                    if chunk and "content" in chunk:
                        yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_chunk', 'content': chunk['content']})}\n\n"
                        
            yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_end'})}\n\n"
