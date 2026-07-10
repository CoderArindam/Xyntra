from enum import Enum
import re
from typing import Dict, Any, Type
from pydantic import BaseModel, Field
from app.ai.gateway.ai_gateway import AIGateway
from app.ai.prompts.registry import PromptRegistry
from app.ai.exceptions import PermissionError

class IntentType(str, Enum):
    CONVERSATIONAL = "CONVERSATIONAL"
    KNOWLEDGE = "KNOWLEDGE"
    WORKSPACE_ACTION = "WORKSPACE_ACTION"

class IntentClassification(BaseModel):
    intent: IntentType = Field(description="The classified intent of the user request")

class IntentRouter:
    """
    Classifies user messages to determine if they need tool execution, 
    general knowledge, or conversational replies.
    """
    
    # Fast regex filter for common conversational greetings/phrases
    CONVERSATIONAL_REGEX = re.compile(
        r"^(hi|hello|hey|good morning|good evening|good night|thanks|thank you|bye|who are you|how are you\??|help\??)$",
        re.IGNORECASE
    )
    
    def __init__(self, gateway: AIGateway):
        self.gateway = gateway
        
    def _fast_filter(self, user_input: str) -> IntentType | None:
        """Stage 1: Deterministic fast classification without LLM."""
        text = user_input.strip()
        if self.CONVERSATIONAL_REGEX.match(text):
            return IntentType.CONVERSATIONAL
            
        # Check FastActionRegistry for deterministic workspace reads
        from app.ai.orchestration.fast_actions import fast_action_registry
        if fast_action_registry.find_match(text):
            return IntentType.WORKSPACE_ACTION
            
        return None
        
    async def classify(self, user_input: str, request_id: str, organization_id: str, user_id: str, llm_context: str = None, user_has_permission = False) -> IntentType:
        print("user has permission", user_has_permission, "from intent_router.py file")
        """
        Classifies the intent, returning one of CONVERSATIONAL, KNOWLEDGE, or WORKSPACE_ACTION.
        Uses a two-stage approach: fast heuristics first, then LLM.
        """
        from app.ai.telemetry.context import Span
        
        with Span("Intent Classification", "IntentRouter") as span:
            # Stage 1: Fast Filter
            fast_intent = self._fast_filter(user_input)
            if fast_intent:
                span.metadata["intent"] = fast_intent.value
                span.metadata["method"] = "fast_filter"
                return fast_intent
                
            # Stage 2: LLM Router
            system_prompt = PromptRegistry.render_prompt(
                agent_name="workspace_assistant",
                prompt_name="router",
                context={},
                version="v1"
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": llm_context if llm_context else user_input}
            ]
            
            try:
                classification_result = await self.gateway.execute_prompt(
                    messages=messages,
                    response_schema=IntentClassification,
                    org_ai_enabled=True,
                    user_has_permission=user_has_permission,
                    workflow_id="intent_routing",
                    request_id=request_id,
                    organization_id=organization_id,
                    user_id=user_id
                )
                
                if isinstance(classification_result, IntentClassification):
                    span.metadata["intent"] = classification_result.intent.value
                    span.metadata["method"] = "llm"
                    return classification_result.intent
                else:
                    span.metadata["intent"] = IntentType.WORKSPACE_ACTION.value
                    span.metadata["method"] = "llm_fallback"
                    return IntentType.WORKSPACE_ACTION # Safe fallback
            except Exception as e:
                if isinstance(e, PermissionError):
                    raise
                # Fallback to WORKSPACE_ACTION if classification fails, planner can figure it out
                span.metadata["intent"] = IntentType.WORKSPACE_ACTION.value
                span.metadata["method"] = "error_fallback"
                return IntentType.WORKSPACE_ACTION
