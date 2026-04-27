from __future__ import annotations

import argparse
from pathlib import Path

from cache_strategies import STRATEGIES
from load_generator import WORKLOADS, append_csv, print_result, run_single


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run all caching experiments")
    parser.add_argument("--requests", type=int, default=10_000)
    parser.add_argument("--duration", type=float, default=None)
    parser.add_argument("--dataset-size", type=int, default=1_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--redis-url", default="redis://localhost:6379/0")
    parser.add_argument("--write-back-flush-every", type=int, default=500)
    parser.add_argument("--output", type=Path, default=Path("results/results.csv"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.output.exists():
        args.output.unlink()

    for workload in WORKLOADS:
        for strategy in STRATEGIES:
            print(f"\n=== strategy={strategy} workload={workload} ===")
            db_path = Path("results") / f"{strategy}_{workload}.sqlite3"
            result = run_single(
                strategy_name=strategy,
                workload_name=workload,
                requests=args.requests,
                dataset_size=args.dataset_size,
                seed=args.seed,
                db_path=db_path,
                redis_url=args.redis_url,
                max_duration_sec=args.duration,
                write_back_flush_every=args.write_back_flush_every,
            )
            append_csv(result, args.output)
            print_result(result)

    print(f"\nSaved CSV: {args.output}")


if __name__ == "__main__":
    main()
