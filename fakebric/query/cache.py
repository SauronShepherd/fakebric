from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from dataclasses import dataclass


def _default(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


@dataclass(frozen=True)
class CachedExecution:
    columns: tuple
    rows: tuple
    warnings: tuple
    plan: tuple
    plan_text: str
    rows_read: int
    bytes_read: int
    backend: str
    planning_ms: float
    execution_ms: float


class QueryCache:
    def __init__(self, max_entries: int = 128) -> None:
        self.max_entries = max_entries
        self._items = OrderedDict()

    def key(self, model, request, tables, data_revision="inline") -> str:
        query = request.model_dump(mode="json", by_alias=True, exclude={"page", "page_size", "timeout_ms"})
        payload = {"modelId": model.id, "revision": model.revision, "query": query, "dataRevision": data_revision, "data": tables}
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=_default).encode()
        return hashlib.sha256(raw).hexdigest()

    def get(self, key):
        item = self._items.get(key)
        if item is not None:
            self._items.move_to_end(key)
        return item

    def put(self, key, value) -> None:
        self._items[key] = value
        self._items.move_to_end(key)
        while len(self._items) > self.max_entries:
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()
