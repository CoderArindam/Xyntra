from typing import Any, Dict, Optional, Type
from pydantic import BaseModel
import uuid

from app.ai.gateway.ai_gateway import AIGateway
from app.ai.agents.base import BaseAgent
from app.ai.context.base import BaseContextBuilder

class AIService:
    """
    Public API for the rest of the application to interact with the AI Platform.
    No other part of the application should instantiate Gateway, Providers, or Agents directly.
    """

    def __init__(self, gateway: AIGateway):
        # Gateway is injected.
        self.gateway = gateway

    def execute_agent(
        self,
        agent: BaseAgent,
        context_builder: BaseContextBuilder,
        user_input: str,
        user_id: int,
        workspace_id: int,
        org_ai_enabled: bool,
        user_has_permission: bool,
        response_schema: Optional[Type[BaseModel]] = None,
        workflow_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> Any:
        """
        Executes a request via an Agent.
        """
        # 1. Build Context
        context = context_builder.build(user_id=user_id, workspace_id=workspace_id)
        
        # 2. Build Messages via Agent
        messages = agent.build_messages(user_input=user_input, context=context)

        # 3. Define Tools
        tools_schema = []
        for tool_cls in agent.available_tools:
            tools_schema.append({
                "type": "function",
                "function": {
                    "name": tool_cls.name,
                    "description": tool_cls.description,
                    # We can use Pydantic's model_json_schema() to generate the parameters dynamically
                    "parameters": tool_cls.input_schema.model_json_schema()
                }
            })

        request_id = str(uuid.uuid4())

        # 4. Execute via Gateway
        result = self.gateway.execute_prompt(
            messages=messages,
            org_ai_enabled=org_ai_enabled,
            user_has_permission=user_has_permission,
            response_schema=response_schema,
            tools=tools_schema if tools_schema else None,
            workflow_id=workflow_id,
            request_id=request_id,
            organization_id=organization_id,
            user_id=str(user_id)
        )

        return result
