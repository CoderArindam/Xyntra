"""Speaker Mapping Strategies (M2.7)."""

from .service import SpeakerMappingService
from .registry import MappingStrategyRegistry
from .strategy import SpeakerMappingStrategy
from .dummy_strategy import DummyMappingStrategy
from .join_order_strategy import JoinOrderMappingStrategy

# Pre-register out-of-the-box strategies
MappingStrategyRegistry.register(DummyMappingStrategy)
MappingStrategyRegistry.register(JoinOrderMappingStrategy)

__all__ = [
    "SpeakerMappingService",
    "MappingStrategyRegistry",
    "SpeakerMappingStrategy",
    "DummyMappingStrategy",
    "JoinOrderMappingStrategy",
]
