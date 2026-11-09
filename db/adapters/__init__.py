"""Registry of state adapters: get_adapter("maharashtra") -> a ready adapter."""
import re

from .base import AdapterError, AdapterResult, BaseAdapter, UnknownStateError
from .karnataka import KarnatakaAdapter
from .maharashtra import MaharashtraAdapter
from .uttar_pradesh import UttarPradeshAdapter

_ADAPTERS = {
    "maharashtra": MaharashtraAdapter,
    "karnataka": KarnatakaAdapter,
    "uttar_pradesh": UttarPradeshAdapter,
}


def available_states():
    return sorted(_ADAPTERS)


def get_adapter(state) -> BaseAdapter:
    """Return the adapter for a state. 'Uttar Pradesh' and 'uttar-pradesh' also work."""
    key = re.sub(r"[\s-]+", "_", str(state).strip().lower())
    adapter_class = _ADAPTERS.get(key)
    if adapter_class is None:
        raise UnknownStateError(
            f"Unknown state {str(state)!r}. Available states: {', '.join(available_states())}")
    return adapter_class()


__all__ = ["AdapterError", "AdapterResult", "BaseAdapter", "UnknownStateError",
           "available_states", "get_adapter"]
