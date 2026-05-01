"""Desktop-local multimodal perception: events, fusion, throttling, desktop capture."""

from jarvis.multimodal.fusion import MultimodalFusionState
from jarvis.multimodal.events import (
    VALID_EVENT_KINDS,
    normalize_multimodal_event,
)

__all__ = [
    "MultimodalFusionState",
    "VALID_EVENT_KINDS",
    "normalize_multimodal_event",
]
