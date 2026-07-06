from pydantic import BaseModel
from typing import Dict, Any

class PerformanceBudgets(BaseModel):
    max_planner_calls: int = 1
    max_composer_calls: int = 1
    max_total_llm_calls: int = 3
    max_prompt_tokens: int = 10000
    max_completion_tokens: int = 4000
    max_execution_time_ms: int = 30000

performance_budgets = PerformanceBudgets()
