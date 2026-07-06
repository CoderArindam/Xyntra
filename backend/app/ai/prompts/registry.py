import os
from typing import Optional
from app.ai.exceptions import AIError

PROMPTS_DIR = os.path.dirname(os.path.abspath(__file__))

class PromptRegistry:
    """
    Registry for loading versioned Markdown prompts.
    Prompts are stored in directories by agent, with versioned filenames.
    e.g. workspace_assistant/system.v1.md
    """

    _cache = {}

    @staticmethod
    def get_prompt(agent_name: str, prompt_name: str, version: Optional[str] = None) -> str:
        """
        Loads a prompt template. If version is None, attempts to load the highest version available.
        (For Phase 1, we assume version is provided or defaults to 'v1').
        """
        version = version or "v1"
        cache_key = f"{agent_name}:{prompt_name}:{version}"
        
        if cache_key in PromptRegistry._cache:
            return PromptRegistry._cache[cache_key]
            
        filepath = os.path.join(PROMPTS_DIR, agent_name, f"{prompt_name}.{version}.md")
        
        if not os.path.exists(filepath):
            raise AIError(f"Prompt not found: {agent_name}/{prompt_name}.{version}.md")
            
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            PromptRegistry._cache[cache_key] = content
            return content

    @staticmethod
    def render_prompt(agent_name: str, prompt_name: str, context: dict, version: Optional[str] = None) -> str:
        """
        Loads and renders a prompt template with the provided context.
        """
        template = PromptRegistry.get_prompt(agent_name, prompt_name, version)
        try:
            return template.format(**context)
        except KeyError as e:
            raise AIError(f"Missing context variable for prompt {prompt_name}: {str(e)}")
