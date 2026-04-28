from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DbMetrics:
    reads: int = 0
    writes: int = 0


class ProductStorage:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.metrics = DbMetrics()

    def setup_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                version INTEGER NOT NULL
            )
            """
        )
        self.connection.commit()

    def seed(self, count: int) -> None:
        self.connection.execute("DELETE FROM products")
        rows = [
            (item_id, f"product-{item_id}", 100 + item_id % 50, 1)
            for item_id in range(1, count + 1)
        ]
        self.connection.executemany(
            "INSERT INTO products(id, name, price, version) VALUES (?, ?, ?, ?)",
            rows,
        )
        self.connection.commit()
        self.reset_metrics()

    def get_product(self, item_id: int) -> dict | None:
        self.metrics.reads += 1
        row = self.connection.execute(
            "SELECT id, name, price, version FROM products WHERE id = ?",
            (item_id,),
        ).fetchone()
        return dict(row) if row else None

    def update_product(self, product: dict) -> None:
        self.metrics.writes += 1
        self.connection.execute(
            """
            INSERT INTO products(id, name, price, version)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                price = excluded.price,
                version = excluded.version
            """,
            (
                product["id"],
                product["name"],
                product["price"],
                product["version"],
            ),
        )
        self.connection.commit()

    def reset_metrics(self) -> None:
        self.metrics = DbMetrics()

    def close(self) -> None:
        self.connection.close()
