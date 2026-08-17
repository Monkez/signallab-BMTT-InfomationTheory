from __future__ import annotations

import threading
import uuid
from collections import OrderedDict
from typing import Any, Literal

import numpy as np


PortDirection = Literal["inputs", "outputs"]
PortValues = dict[str, dict[PortDirection, dict[str, np.ndarray]]]


def _format_value(value: Any) -> str:
    scalar = value.item() if hasattr(value, "item") else value
    if isinstance(scalar, complex):
        return f"{scalar.real:.8g}{scalar.imag:+.8g}j"
    if isinstance(scalar, float):
        return f"{scalar:.10g}"
    return str(scalar)


class SnapshotStore:
    """Small in-memory LRU of representative frames, fetched lazily by port."""

    def __init__(self, capacity: int = 4):
        self.capacity = capacity
        self._items: OrderedDict[str, PortValues] = OrderedDict()
        self._lock = threading.RLock()

    def register(self, values: PortValues) -> str:
        snapshot_id = uuid.uuid4().hex
        with self._lock:
            self._items[snapshot_id] = values
            self._items.move_to_end(snapshot_id)
            while len(self._items) > self.capacity:
                self._items.popitem(last=False)
        return snapshot_id

    def page(
        self,
        snapshot_id: str,
        node_id: str,
        direction: PortDirection,
        port: str,
        offset: int,
        limit: int,
    ) -> dict[str, Any] | None:
        with self._lock:
            snapshot = self._items.get(snapshot_id)
            if snapshot is None:
                return None
            self._items.move_to_end(snapshot_id)
            try:
                array = snapshot[node_id][direction][port].reshape(-1)
            except KeyError:
                return None
            total = int(array.size)
            start = min(offset, total)
            end = min(start + limit, total)
            return {
                "snapshot_id": snapshot_id,
                "node_id": node_id,
                "direction": direction,
                "port": port,
                "dtype": str(array.dtype),
                "shape": list(snapshot[node_id][direction][port].shape),
                "total": total,
                "offset": start,
                "limit": limit,
                "values": [_format_value(value) for value in array[start:end]],
            }


store = SnapshotStore()
