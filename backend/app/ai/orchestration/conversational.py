import re
from typing import Optional

class ConversationTemplateRegistry:
    """
    Deterministic response provider for common conversational intents (greetings, help, etc).
    Ensures 0 LLM calls for simple known inputs.
    """
    
    _templates = {
        r"^(hi|hello|hey|good morning|good evening|good night)$": (
            "Hello! I am your ProSync Assistant. I can help you manage your projects, boards, and tasks. "
            "How can I assist you today?"
        ),
        r"^(how are you\??|what's up\??|hows it going\??)$": (
            "I'm functioning perfectly, thank you! Ready to help you manage your workspace. What do you need?"
        ),
        r"^(who are you\??|what can you do\??|what are you\??)$": (
            "I am the ProSync Assistant. I'm integrated directly into your workspace. "
            "I can list projects, manage boards, create tasks, and answer questions about project management."
        ),
        r"^(help\??)$": (
            "I can help you with your workspace! Try asking me to:\n"
            "- List my projects\n"
            "- Create a task for bug fixing\n"
            "- Show my assigned tasks\n"
            "- What is Scrum?"
        ),
        r"^(thanks|thank you)$": (
            "You're welcome! Let me know if you need anything else."
        ),
        r"^(bye|goodbye)$": (
            "Goodbye! Have a productive day."
        )
    }
    
    def __init__(self):
        self._compiled_templates = {
            re.compile(pattern, re.IGNORECASE): response
            for pattern, response in self._templates.items()
        }

    def get_response(self, text: str) -> Optional[str]:
        text = text.strip()
        for pattern, response in self._compiled_templates.items():
            if pattern.match(text):
                return response
        return None

# Singleton instance
conversation_registry = ConversationTemplateRegistry()
