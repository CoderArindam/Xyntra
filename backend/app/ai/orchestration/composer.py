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
                    
        if parts:
            return "\n\n---\n\n".join(parts)
            
        return None

template_registry = TemplateRegistry()

# Workspace read actions
list_projects_renderer = lambda output: render_list(
    f"You currently have {len(output.get('projects', []))} projects.", 
    output.get("projects", []), 
    display_field="name"
) if output and isinstance(output, dict) else None

template_registry.register("list_projects", list_projects_renderer)
template_registry.register("list_boards", list_projects_renderer)

list_tasks_renderer = lambda output: render_list(
    f"You currently have {len(output.get('tasks', []))} tasks.",
    output.get("tasks", []),
    display_field="title",
    secondary_field="column_name"
) if output and isinstance(output, dict) else None

template_registry.register("list_tasks", list_tasks_renderer)

template_registry.register("get_users", lambda output: render_list(
    f"Found {len(output.get('users', []))} workspace members.",
    output.get("users", []),
    display_field="first_name",
    secondary_field="email"
) if output and isinstance(output, dict) else None)

template_registry.register("get_task_details", lambda output: render_entity(
    "Task Details",
    output.get("task", {}),
    fields=["title", "column_name", "priority", "assignee_id"]
) if output and isinstance(output, dict) else None)

# Domain tool actions

template_registry.register("create_task", lambda output: render_success(
    "Create Task", output.get("message", "Task created successfully")
) if output and isinstance(output, dict) else None)

template_registry.register("update_task", lambda output: render_success(
    "Update Task", output.get("message", "Task updated successfully")
) if output and isinstance(output, dict) else None)

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
                    user_has_permission=True,
                    workflow_id="response_composition",
                    request_id=context.request_id,
                    organization_id=context.organization_id,
                    user_id=str(context.current_user.get("id"))
                )
                
                async for chunk in stream_gen:
                    if chunk and "content" in chunk:
                        yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_chunk', 'content': chunk['content']})}\n\n"
                        
            yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_end'})}\n\n"
