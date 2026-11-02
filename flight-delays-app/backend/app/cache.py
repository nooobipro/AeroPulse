"""Простой потокобезопасный LRU-кэш с TTL. Данные статичные, поэтому кэш агрессивный."""
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

from app.config import settings


class TTLCache:
    def __init__(self, maxsize: int = 1024, ttl: float = 3600.0):
        self.maxsize, self.ttl = maxsize, ttl
        self._data: OrderedDict[Any, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def get_or_set(self, key: Any, factory: Callable[[], Any]) -> Any:
        now = time.monotonic()
        with self._lock:
            item = self._data.get(key)
            if item and item[0] > now:
                self._data.move_to_end(key)
                return item[1]
        value = factory()  # вычисляем вне блокировки: фабрики могут вызывать кэш рекурсивно
        with self._lock:
            self._data[key] = (now + self.ttl, value)
            self._data.move_to_end(key)
            while len(self._data) > self.maxsize:
                self._data.popitem(last=False)
        return value

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


cache = TTLCache(ttl=settings.cache_ttl_seconds)
