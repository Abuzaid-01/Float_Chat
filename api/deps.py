"""
Shared, lazily created components for the API.

The query processor loads an embedding model and a FAISS index, so exactly one
is built per process and every route uses it.  Creation is guarded by a lock
because routes run on worker threads.
"""

import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple

from database.db_setup import DatabaseSetup

_lock = threading.RLock()
_instances: Dict[str, Any] = {}


def _get(name: str, factory: Callable[[], Any]) -> Any:
    instance = _instances.get(name)
    if instance is None:
        with _lock:
            instance = _instances.get(name)
            if instance is None:
                instance = factory()
                _instances[name] = instance
    return instance


def get_db() -> DatabaseSetup:
    return _get("db", DatabaseSetup)


def get_query_processor():
    def build():
        from rag_engine.query_processor import QueryProcessor
        return QueryProcessor()
    return _get("query_processor", build)


def get_intent_classifier():
    def build():
        from rag_engine.intent_classifier import IntentClassifier
        return IntentClassifier()
    return _get("intent_classifier", build)


def get_analytics():
    def build():
        from advanced_analytics.profile_analytics import AdvancedProfileAnalytics
        return AdvancedProfileAnalytics()
    return _get("analytics", build)


def loaded_components() -> Dict[str, bool]:
    """Which components have finished loading (for the health endpoint)."""
    return {name: name in _instances for name in ("query_processor", "intent_classifier", "analytics")}


def warm_up() -> None:
    """Load the heavy components in the background so the first question is not slow."""
    def load():
        try:
            get_intent_classifier()
            get_query_processor().get_dataset_range()
        except Exception as error:  # the first real request will surface the problem
            print(f"⚠️  Warm-up failed: {error}")

    threading.Thread(target=load, name="warm-up", daemon=True).start()


class TTLCache:
    """Tiny time-based cache for read-only endpoint results on a static dataset."""

    def __init__(self, ttl_seconds: float):
        self.ttl = ttl_seconds
        self._lock = threading.Lock()
        self._values: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._values.get(key)
            if entry and time.time() - entry[0] < self.ttl:
                return entry[1]
            return None

    def set(self, key: str, value: Any) -> Any:
        with self._lock:
            self._values[key] = (time.time(), value)
        return value
