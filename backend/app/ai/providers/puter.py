from app.ai.providers.openai import OpenAIProvider
from app.ai.exceptions import AuthenticationError
from openai import AsyncOpenAI

class PuterProvider(OpenAIProvider):
    """Puter implementation of the AIProvider interface, using OpenAI compatibility."""
    
    def __init__(self, api_key: str, model: str):
        # We bypass OpenAIProvider's __init__ because we need to inject the base_url
        self.api_key = api_key
        self.model = model
        
        if not self.api_key:
            raise AuthenticationError("Puter API key is missing.")
            
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.puter.com/puterai/openai/v1/"
        )
