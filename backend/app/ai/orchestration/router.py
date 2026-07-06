from enum import Enum
import re
from typing import Dict, Any, Type
from pydantic import BaseModel, Field
from app.ai.gateway.ai_gateway import AIGateway
from app.ai.prompts.registry import PromptRegistry

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
        return None
        
    async def classify(self, user_input: str, request_id: str, organization_id: str, user_id: str) -> IntentType:
        """
        Classifies the intent, returning one of CONVERSATIONAL, KNOWLEDGE, or WORKSPACE_ACTION.
        Uses a two-stage approach: fast heuristics first, then LLM.
        """
        # Stage 1: Fast Filter
        fast_intent = self._fast_filter(user_input)
        if fast_intent:
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
            {"role": "user", "content": user_input}
        ]
        
        try:
            classification_result = self.gateway.execute_prompt(
                messages=messages,
                response_schema=IntentClassification,
                org_ai_enabled=True,
                user_has_permission=True,
                workflow_id="intent_routing",
                request_id=request_id,
                organization_id=organization_id,
                user_id=user_id
            )
            
            if isinstance(classification_result, IntentClassification):
                return classification_result.intent
            else:
                return IntentType.WORKSPACE_ACTION # Safe fallback
        except Exception as e:
            # Fallback to WORKSPACE_ACTION if classification fails, planner can figure it out
            return IntentType.WORKSPACE_ACTION
