import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.ai.gateway.ai_gateway import AIGateway
from app.ai.schemas.planning import ExecutionPlan
from app.ai.telemetry.context import Span

class ClarificationDecision(BaseModel):
    decision: str = Field(..., description="Must be 'RESUME', 'CANCEL', or 'NEW_INTENT'")
    updated_plan: Optional[Dict[str, Any]] = Field(None, description="If RESUME, the original plan updated with the user's provided information")
    reasoning: str = Field(..., description="Brief explanation for the decision")

class ClarificationRouter:
    """
    Decides how to handle a user's message when there is a pending clarification.
    """
    def __init__(self, gateway: AIGateway):
        self.gateway = gateway

    async def resolve(self, user_input: str, pending_plan: ExecutionPlan, missing_fields: list[str], request_id: str, organization_id: str, user_id: str, user_has_permission: bool = True) -> ClarificationDecision:
        with Span("Resolve Clarification", "ClarificationRouter") as span:
            system_prompt = f"""You are routing a user's response to a pending clarification question.

The assistant previously paused execution because the following fields were missing:
{missing_fields}

The pending plan was:
{pending_plan.model_dump_json(indent=2)}

The user just replied. Your job is to classify the user's reply into one of three categories:

1. "RESUME": The user provided the missing information. You must return `updated_plan` containing the exact pending plan, but with the missing fields populated based on the user's input.
2. "CANCEL": The user wants to cancel, stop, abort, or forget the current pending action.
3. "NEW_INTENT": The user completely ignored the question and started a brand new request or asked a completely unrelated question (e.g. "What's the weather?").

Return a JSON object matching this schema:
{{
  "decision": "RESUME" | "CANCEL" | "NEW_INTENT",
  "updated_plan": {{ ... }},
  "reasoning": "..."
}}
"""
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
            
            result = await self.gateway.execute_prompt(
                messages=messages,
                org_ai_enabled=True,
                user_has_permission=user_has_permission,
                response_schema=ClarificationDecision,
                workflow_id="clarification_resolution",
                request_id=request_id,
                organization_id=organization_id,
                user_id=user_id
            )
            
            span.metadata["decision"] = result.decision
            return result
