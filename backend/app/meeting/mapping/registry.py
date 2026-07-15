"""Registry for Mapping Strategies (Open/Closed Principle)."""

from typing import Dict, Type

from app.meeting.exceptions import SpeakerMappingError
from .strategy import SpeakerMappingStrategy


class MappingStrategyRegistry:
    """Central registry for all available mapping strategies."""
    
    _registry: Dict[str, Type[SpeakerMappingStrategy]] = {}

    @classmethod
    def register(cls, strategy_class: Type[SpeakerMappingStrategy]) -> None:
        """Register a strategy class by its strategy_name property."""
        # Instantiate temporarily just to read the property
        name = strategy_class().strategy_name
        cls._registry[name] = strategy_class

    @classmethod
    def get(cls, name: str) -> SpeakerMappingStrategy:
        """Retrieve an instantiated strategy by name."""
        if name not in cls._registry:
            raise SpeakerMappingError(f"Unknown mapping strategy: '{name}'")
        return cls._registry[name]()
