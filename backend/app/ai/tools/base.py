from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel
import time

class BaseTool(ABC):
    """
    Base class for all AI tools in the ecosystem.
    Tools must be stateless and rely on injected Application Services.
    """
    name: str
    description: str
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]
    
    # Generic Tool Metadata for governance
    category: str = "general"
    version: str = "1.0"
    is_write_action: bool = False
    
    # Execution Metadata for Phase 3.3
    from app.ai.schemas.planning import RiskLevel
    risk_level: RiskLevel = RiskLevel.SAFE
    action: str = ""  # The abstract action this tool fulfills (e.g., 'find_project')

    @abstractmethod
    async def execute(self, params: BaseModel, current_user: dict, services: Dict[str, Any]) -> Any:
        """
        Execute the tool logic using the provided parameters and services.
        
        Args:
            params: Validated Pydantic model parameters
            current_user: The user context executing the tool
            services: Dictionary of injected domain services
            
        Returns:
            The result of the tool execution
        """
        pass

    async def run(self, params: BaseModel, current_user: dict, services: Dict[str, Any], telemetry=None) -> Any:
        """
        Wrapper around execute to handle telemetry, policies, and error catching.
        """
        from app.ai.telemetry.tracker import tool_telemetry
        tracker = telemetry or tool_telemetry
        
        # [Safety Hook] Check permissions, RBAC, and Organization Policies here
        if self.is_write_action:
            # Future: Execute pre-flight check for write actions
            pass

        # [Safety Hook] Audit logging point here
        
        start_time = time.time()
        try:
            result = await self.execute(params, current_user, services)
            
            tracker.record_tool_execution(
                tool_name=self.name,
                latency=time.time() - start_time,
                success=True
            )
            return result
        except Exception as e:
            tracker.record_tool_execution(
                tool_name=self.name,
                latency=time.time() - start_time,
                success=False,
                error=str(e)
            )
            raise
