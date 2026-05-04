from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import redis

from cache_strategies import STRATEGIES, CacheStrategy
from storage import ProductStorage


WORKLOADS = {
    "read-heavy": 0.80,
    "balanced": 0.50,
    "write-heavy": 0.20,
}


@dataclass(frozen=True)
class Operation:
    kind: str
    item_id: int
    price_delta: int


@dataclass
class RunResult:
    strategy: str
    workload: str
    requests: int
    read_ratio: float
    duration_sec: float
    throughput_rps: float
    avg_latency_ms: float
    p95_latency_ms: float
    db_reads: int
    db_writes: int
    db_total: int
    cache_hits: int
    cache_misses: int
    cache_hit_rate: float
    write_back_pending_max: int
    write_back_pending_after_finish: int


def build_operations(
    requests: int,
    read_ratio: float,
    dataset_size: int,
    seed: int,
) -> list[Operation]:
    randomizer = random.Random(seed)
    operations: list[Operation] = []

    for _ in range(requests):
        kind = "read" if randomizer.random() < read_ratio else "write"
        item_id = randomizer.randint(1, dataset_size)
        price_delta = randomizer.choice([-3, -2, -1, 1, 2, 3])
        operations.append(Operation(kind, item_id, price_delta))

    return operations


def run_operations(
    strategy: CacheStrategy,
    operations: Iterable[Operation],
    max_duration_sec: float | None = None,
) -> tuple[int, float, list[float]]:
    started_at = time.perf_counter()
    latencies_ms: list[float] = []
    completed = 0

    for operation in operations:
        if max_duration_sec is not None and time.perf_counter() - started_at >= max_duration_sec:
            break

        request_started_at = time.perf_counter()
        if operation.kind == "read":
            strategy.read_product(operation.item_id)
        else:
            strategy.write_product(operation.item_id, operation.price_delta)
        latencies_ms.append((time.perf_counter() - request_started_at) * 1000)
        completed += 1

    duration = time.perf_counter() - started_at
    strategy.finish()
    return completed, duration, latencies_ms


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    index = int(round((len(values) - 1) * percent))
    return values[index]


def reset_redis(redis_client: redis.Redis) -> None:
    redis_client.flushdb()


def run_single(
    strategy_name: str,
    workload_name: str,
    requests: int,
    dataset_size: int,
    seed: int,
    db_path: Path,
    redis_url: str,
    max_duration_sec: float | None,
    write_back_flush_every: int,
) -> RunResult:
    if strategy_name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy_name}")
    if workload_name not in WORKLOADS:
        raise ValueError(f"Unknown workload: {workload_name}")

    redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
    redis_client.ping()
    reset_redis(redis_client)

    storage = ProductStorage(db_path)
    storage.setup_schema()
    storage.seed(dataset_size)

    read_ratio = WORKLOADS[workload_name]
    operations = build_operations(requests, read_ratio, dataset_size, seed)
    strategy = STRATEGIES[strategy_name](
        storage,
        redis_client,
        write_back_flush_every=write_back_flush_every,
    )

    completed, duration, latencies_ms = run_operations(
        strategy,
        operations,
        max_duration_sec=max_duration_sec,
    )
    pending_after_finish = strategy.pending_writes()

    result = RunResult(
        strategy=strategy_name,
        workload=workload_name,
        requests=completed,
        read_ratio=read_ratio,
        duration_sec=duration,
        throughput_rps=completed / duration if duration else 0.0,
        avg_latency_ms=statistics.fmean(latencies_ms) if latencies_ms else 0.0,
        p95_latency_ms=percentile(latencies_ms, 0.95),
        db_reads=storage.metrics.reads,
        db_writes=storage.metrics.writes,
        db_total=storage.metrics.reads + storage.metrics.writes,
        cache_hits=strategy.metrics.hits,
        cache_misses=strategy.metrics.misses,
        cache_hit_rate=strategy.metrics.hit_rate,
        write_back_pending_max=strategy.metrics.pending_max,
        write_back_pending_after_finish=pending_after_finish,
    )

    storage.close()
    redis_client.close()
    return result


def append_csv(result: RunResult, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_path.exists()
    with output_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(asdict(result).keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(asdict(result))


def print_result(result: RunResult) -> None:
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


def print_summary(result: RunResult) -> None:
    print(
        f"{result.strategy:13} | {result.workload:11} | "
        f"rps={result.throughput_rps:8.2f} | "
        f"avg={result.avg_latency_ms:6.3f} ms | "
        f"db={result.db_total:5} | "
        f"hit={result.cache_hit_rate * 100:6.2f}% | "
        f"wb_pending_max={result.write_back_pending_max}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Caching strategy load generator")
    parser.add_argument("--strategy", choices=sorted(STRATEGIES), required=True)
    parser.add_argument("--workload", choices=sorted(WORKLOADS), required=True)
    parser.add_argument("--requests", type=int, default=10_000)
    parser.add_argument("--duration", type=float, default=None)
    parser.add_argument("--dataset-size", type=int, default=1_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--db-path", type=Path, default=Path("results/app.sqlite3"))
    parser.add_argument("--redis-url", default="redis://localhost:6379/0")
    parser.add_argument("--write-back-flush-every", type=int, default=500)
    parser.add_argument("--output", type=Path, default=Path("results/results.csv"))
    parser.add_argument("--format", choices=["summary", "json"], default="summary")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_single(
        strategy_name=args.strategy,
        workload_name=args.workload,
        requests=args.requests,
        dataset_size=args.dataset_size,
        seed=args.seed,
        db_path=args.db_path,
        redis_url=args.redis_url,
        max_duration_sec=args.duration,
        write_back_flush_every=args.write_back_flush_every,
    )
    append_csv(result, args.output)
    if args.format == "json":
        print_result(result)
    else:
        print_summary(result)


if __name__ == "__main__":
    main()
