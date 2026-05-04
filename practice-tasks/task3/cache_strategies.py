from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass

import redis

from storage import ProductStorage


@dataclass
class CacheMetrics:
    hits: int = 0
    misses: int = 0
    pending_max: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


class CacheStrategy(ABC):
    name = "base"

    def __init__(
        self,
        storage: ProductStorage,
        redis_client: redis.Redis,
        cache_ttl_seconds: int = 300,
        write_back_flush_every: int = 100,
    ) -> None:
        self.storage = storage
        self.redis = redis_client
        self.cache_ttl_seconds = cache_ttl_seconds
        self.write_back_flush_every = write_back_flush_every
        self.metrics = CacheMetrics()
        self._writes_since_flush = 0

    def read_product(self, item_id: int) -> dict | None:
        cached = self.redis.get(self._cache_key(item_id))
        if cached is not None:
            self.metrics.hits += 1
            return json.loads(cached)

        self.metrics.misses += 1
        product = self.storage.get_product(item_id)
        if product is not None:
            self._set_cache(product)
        return product

    @abstractmethod
    def write_product(self, item_id: int, price_delta: int) -> dict:
        raise NotImplementedError

    def finish(self) -> None:

    def pending_writes(self) -> int:
        return 0

    def _cache_key(self, item_id: int) -> str:
        return f"product:{item_id}"

    def _dirty_key(self, item_id: int) -> str:
        return f"dirty:{item_id}"

    def _set_cache(self, product: dict) -> None:
        self.redis.setex(
            self._cache_key(product["id"]),
            self.cache_ttl_seconds,
            json.dumps(product),
        )

    def _next_product_state(self, item_id: int, price_delta: int) -> dict:
        current = self.read_product(item_id)
        if current is None:
            current = {
                "id": item_id,
                "name": f"product-{item_id}",
                "price": 100,
                "version": 0,
            }
        return {
            "id": item_id,
            "name": current["name"],
            "price": max(1, current["price"] + price_delta),
            "version": current["version"] + 1,
        }


class LazyLoadingStrategy(CacheStrategy):
    name = "lazy_loading"

    def write_product(self, item_id: int, price_delta: int) -> dict:
        product = self._next_product_state(item_id, price_delta)
        self.storage.update_product(product)
        self.redis.delete(self._cache_key(item_id))
        return product


class WriteThroughStrategy(CacheStrategy):
    name = "write_through"

    def write_product(self, item_id: int, price_delta: int) -> dict:
        product = self._next_product_state(item_id, price_delta)
        self.storage.update_product(product)
        self._set_cache(product)
        return product


class WriteBackStrategy(CacheStrategy):
    name = "write_back"
    dirty_set_key = "dirty-products"

    def write_product(self, item_id: int, price_delta: int) -> dict:
        product = self._next_product_state(item_id, price_delta)
        self._set_cache(product)
        self.redis.set(self._dirty_key(item_id), json.dumps(product))
        self.redis.sadd(self.dirty_set_key, item_id)
        self._writes_since_flush += 1
        self.metrics.pending_max = max(self.metrics.pending_max, self.pending_writes())

        if self._writes_since_flush >= self.write_back_flush_every:
            self.flush()
        return product

    def flush(self) -> int:
        dirty_ids = [int(item_id) for item_id in self.redis.smembers(self.dirty_set_key)]
        flushed = 0
        for item_id in dirty_ids:
            payload = self.redis.get(self._dirty_key(item_id))
            if payload is None:
                self.redis.srem(self.dirty_set_key, item_id)
                continue

            self.storage.update_product(json.loads(payload))
            self.redis.delete(self._dirty_key(item_id))
            self.redis.srem(self.dirty_set_key, item_id)
            flushed += 1

        self._writes_since_flush = 0
        return flushed

    def finish(self) -> None:
        self.flush()

    def pending_writes(self) -> int:
        return self.redis.scard(self.dirty_set_key)


STRATEGIES = {
    LazyLoadingStrategy.name: LazyLoadingStrategy,
    WriteThroughStrategy.name: WriteThroughStrategy,
    WriteBackStrategy.name: WriteBackStrategy,
}
