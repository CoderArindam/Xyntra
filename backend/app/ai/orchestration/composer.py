import json
from typing import Dict, Any, AsyncGenerator
from app.ai.schemas.planning import ExecutionResult, ExecutionContext
from app.ai.gateway.ai_gateway import AIGateway
from app.ai.prompts.registry import PromptRegistry

class ResponseComposer:
    """
    Transforms an ExecutionResult into a user-friendly conversational response.
    Uses deterministic templates where possible to save tokens and latency,
    falling back to the LLM for complex summaries.
    """
    
    def __init__(self, gateway: AIGateway):
        self.gateway = gateway
        
    def _get_template_response(self, result: ExecutionResult) -> str | None:
        """
        Stage 1: Generate response using simple templates based on tool metrics.
        Returns a string if a template matches, or None if it's too complex.
        """
        metrics = result.tool_metrics
        
        # Simple read queries
        if len(metrics) == 1:
            if metrics.get("list_boards", 0) > 0:
                # We can't know the exact count without looking at the payload, 
                # but we can provide a generic success message
                return "I have found the boards you requested. They should be visible in the results."
            if metrics.get("list_tasks", 0) > 0:
                return "I have retrieved the tasks for the requested board."
                
        # Simple write actions (when implemented)
        if metrics.get("create_board", 0) == 1 and len(metrics) == 1:
            return "The board has been successfully created."
        if metrics.get("create_task", 0) == 1 and len(metrics) == 1:
            return "The task has been successfully created."
            
        return None
        
    async def compose(self, result: ExecutionResult, context: ExecutionContext) -> AsyncGenerator[str, None]:
        """
        Generates and yields the response as assistant_message_chunk events.
        """
        # Start assistant message
        yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_start', 'execution_id': context.execution_id})}\n\n"
        
        template_response = self._get_template_response(result)
        
        if template_response:
            yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_chunk', 'content': template_response})}\n\n"
        else:
            # Stage 2: Complex LLM response
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
            
            for chunk in stream_gen:
                if chunk and "content" in chunk:
                    yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_chunk', 'content': chunk['content']})}\n\n"
                    
        # End assistant message
        yield f"data: {json.dumps({'v': '1.0', 'type': 'assistant_message_end'})}\n\n"
