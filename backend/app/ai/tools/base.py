from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, List
from pydantic import BaseModel
import time
from app.ai.schemas.planning import RiskLevel

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
    
    risk_level: RiskLevel = RiskLevel.SAFE
    action: str = ""  # The abstract action this tool fulfills (e.g., 'find_project')
    required_roles: Optional[List[str]] = None  # List of allowed roles, e.g. ["MANAGER", "SUPER_ADMIN"]. None allows all authenticated roles.

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
        if self.required_roles is not None:
            user_role = (current_user.get("role") or "MEMBER").upper()
            if user_role not in [r.upper() for r in self.required_roles]:
                from app.ai.exceptions import PermissionError
                raise PermissionError(
                    f"You do not have permission to perform action '{self.action or self.name}'. "
                    f"Only {', '.join(sorted(self.required_roles))} can perform task and project management actions."
                )

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
