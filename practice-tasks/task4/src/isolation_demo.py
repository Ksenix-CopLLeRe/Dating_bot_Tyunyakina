import argparse
import os
import threading
import time
from pathlib import Path

import mysql.connector
import psycopg2


POSTGRES_DATABASE_URL = os.getenv(
    "POSTGRES_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5433/isolation_practice",
)

MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3307")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "mysql"),
    "database": os.getenv("MYSQL_DATABASE", "isolation_practice"),
}


def pg_connect():
    return psycopg2.connect(POSTGRES_DATABASE_URL)


def mysql_connect():
    return mysql.connector.connect(**MYSQL_CONFIG)


def log(scenario, transaction, message):
    now = time.strftime("%H:%M:%S")
    print(f"[{now}] [{scenario}] [{transaction}] {message}", flush=True)


def run_sql_file(path):
    sql = Path(path).read_text(encoding="utf-8")
    with pg_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


def run_mysql_sql_file(path):
    sql = Path(path).read_text(encoding="utf-8")
    conn = mysql_connect()
    try:
        cur = conn.cursor()
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement:
                cur.execute(statement)
        conn.commit()
    finally:
        conn.close()


def reset_data():
    schema_path = Path(__file__).resolve().parent.parent / "sql" / "01_schema.sql"
    run_sql_file(schema_path)


def reset_mysql_dirty_data():
    schema_path = (
        Path(__file__).resolve().parent.parent / "sql" / "02_mysql_dirty_schema.sql"
    )
    run_mysql_sql_file(schema_path)


def fetch_one(cur, query, params=None):
    cur.execute(query, params or ())
    return cur.fetchone()[0]


def print_final_state(scenario):
    with pg_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, owner_name, balance FROM accounts ORDER BY id")
            accounts = cur.fetchall()
            cur.execute(
                "SELECT category, count(*) FROM products GROUP BY category ORDER BY category"
            )
            products = cur.fetchall()

    log(scenario, "DB", f"accounts = {accounts}")
    log(scenario, "DB", f"product counts = {products}")


def print_mysql_dirty_final_state(scenario):
    conn = mysql_connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, owner_name, balance FROM accounts ORDER BY id")
        accounts = cur.fetchall()
    finally:
        conn.close()

    log(scenario, "MySQL DB", f"accounts = {accounts}")


def dirty_read_attempt():
    scenario = "dirty_read_mysql"
    reset_mysql_dirty_data()
    writer_updated = threading.Event()
    reader_finished = threading.Event()

    def t1():
        conn = mysql_connect()
        try:
            cur = conn.cursor()
            cur.execute("START TRANSACTION")
            log(
                scenario,
                "T1",
                "START TRANSACTION; меняем balance Anna на 777, но не COMMIT",
            )
            cur.execute("UPDATE accounts SET balance = 777 WHERE id = 1")
            writer_updated.set()
            reader_finished.wait()
            log(scenario, "T1", "ROLLBACK; незакоммиченное изменение отменено")
            conn.rollback()
        finally:
            conn.close()

    def t2():
        writer_updated.wait()
        conn = mysql_connect()
        try:
            cur = conn.cursor()
            cur.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
            cur.execute("START TRANSACTION")
            log(scenario, "T2", "START TRANSACTION READ UNCOMMITTED; читаем balance Anna")
            balance = fetch_one(cur, "SELECT balance FROM accounts WHERE id = 1")
            log(
                scenario,
                "T2",
                f"увидели balance = {balance}; это незакоммиченное значение из T1",
            )
            conn.commit()
            log(scenario, "T2", "COMMIT")
        finally:
            reader_finished.set()
            conn.close()

    run_threads(t1, t2)
    print_mysql_dirty_final_state(scenario)


def non_repeatable_read():
    scenario = "non_repeatable_read"
    reset_data()
    first_read_done = threading.Event()
    writer_committed = threading.Event()

    def t1():
        conn = pg_connect()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN ISOLATION LEVEL READ COMMITTED")
            log(scenario, "T1", "BEGIN READ COMMITTED")
            first_balance = fetch_one(cur, "SELECT balance FROM accounts WHERE id = 1")
            log(scenario, "T1", f"первое чтение balance Anna = {first_balance}")
            first_read_done.set()
            writer_committed.wait()
            second_balance = fetch_one(cur, "SELECT balance FROM accounts WHERE id = 1")
            log(scenario, "T1", f"второе чтение balance Anna = {second_balance}")
            log(scenario, "T1", "одно и то же чтение в транзакции вернуло разные данные")
            conn.commit()
        finally:
            conn.close()

    def t2():
        first_read_done.wait()
        conn = pg_connect()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN")
            log(scenario, "T2", "BEGIN; меняем balance Anna на 500")
            cur.execute("UPDATE accounts SET balance = 500 WHERE id = 1")
            conn.commit()
            log(scenario, "T2", "COMMIT")
        finally:
            writer_committed.set()
            conn.close()

    run_threads(t1, t2)
    print_final_state(scenario)


def phantom_read():
    scenario = "phantom_read"
    reset_data()
    first_read_done = threading.Event()
    writer_committed = threading.Event()

    def t1():
        conn = pg_connect()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN ISOLATION LEVEL READ COMMITTED")
            log(scenario, "T1", "BEGIN READ COMMITTED")
            first_count = fetch_one(
                cur, "SELECT count(*) FROM products WHERE category = 'book'"
            )
            log(scenario, "T1", f"первый count(book) = {first_count}")
            first_read_done.set()
            writer_committed.wait()
            second_count = fetch_one(
                cur, "SELECT count(*) FROM products WHERE category = 'book'"
            )
            log(scenario, "T1", f"второй count(book) = {second_count}")
            log(scenario, "T1", "появилась фантомная строка, подходящая под WHERE")
            conn.commit()
        finally:
            conn.close()

    def t2():
        first_read_done.wait()
        conn = pg_connect()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN")
            log(scenario, "T2", "BEGIN; добавляем новую книгу")
            cur.execute(
                """
                INSERT INTO products (category, title, price)
                VALUES ('book', 'Phantom rows in SQL', 900)
                """
            )
            conn.commit()
            log(scenario, "T2", "COMMIT")
        finally:
            writer_committed.set()
            conn.close()

    run_threads(t1, t2)
    print_final_state(scenario)


def lost_update():
    scenario = "lost_update"
    reset_data()
    both_read = threading.Barrier(2)

    def withdraw(transaction, amount, pause_after_read):
        conn = pg_connect()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN ISOLATION LEVEL READ COMMITTED")
            balance = fetch_one(cur, "SELECT balance FROM accounts WHERE id = 1")
            new_balance = balance - amount
            log(
                scenario,
                transaction,
                f"прочитали {balance}; хотим списать {amount}; рассчитали {new_balance}",
            )
            both_read.wait()
            time.sleep(pause_after_read)
            cur.execute("UPDATE accounts SET balance = %s WHERE id = 1", (new_balance,))
            log(scenario, transaction, f"UPDATE balance = {new_balance}")
            conn.commit()
            log(scenario, transaction, "COMMIT")
        finally:
            conn.close()

    run_threads(
        lambda: withdraw("T1", 100, 0.0),
        lambda: withdraw("T2", 200, 0.3),
    )

    with pg_connect() as conn:
        with conn.cursor() as cur:
            balance = fetch_one(cur, "SELECT balance FROM accounts WHERE id = 1")
    log(
        scenario,
        "RESULT",
        f"финальный balance Anna = {balance}; корректно было бы 700, одно списание потеряно",
    )
    print_final_state(scenario)


def run_threads(*targets):
    threads = [threading.Thread(target=target) for target in targets]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


SCENARIOS = {
    "dirty": dirty_read_attempt,
    "non-repeatable": non_repeatable_read,
    "phantom": phantom_read,
    "lost-update": lost_update,
}


def main():
    parser = argparse.ArgumentParser(
        description="Демонстрация аномалий изоляции транзакций в PostgreSQL и MySQL"
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        choices=[*SCENARIOS.keys(), "all", "init"],
        default="all",
        help="Какой сценарий запустить",
    )
    args = parser.parse_args()

    if args.scenario == "init":
        reset_data()
        reset_mysql_dirty_data()
        print("Базы данных PostgreSQL/MySQL и тестовые данные пересозданы.")
        return

    if args.scenario == "all":
        for name, scenario in SCENARIOS.items():
            print()
            print("=" * 80)
            print(f"SCENARIO: {name}")
            print("=" * 80)
            scenario()
        return

    SCENARIOS[args.scenario]()


if __name__ == "__main__":
    main()
