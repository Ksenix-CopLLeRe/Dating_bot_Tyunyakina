import subprocess
import time
import csv
import os

TESTS = [
    {"broker": "redis", "size": 1024,   "rate": 1000,  "duration": 30, "sent": 30003,  "name": "base_redis"},
    {"broker": "rabbit", "size": 1024,  "rate": 1000,  "duration": 30, "sent": 30003,  "name": "base_rabbit"},

    {"broker": "redis", "size": 128,    "rate": 1000,  "duration": 30, "sent": 30000,  "name": "size_128_redis"},
    {"broker": "redis", "size": 10240,  "rate": 1000,  "duration": 30, "sent": 30000,  "name": "size_10kb_redis"},
    {"broker": "redis", "size": 102400, "rate": 1000,  "duration": 30, "sent": 30000,  "name": "size_100kb_redis"},

    {"broker": "rabbit", "size": 128,    "rate": 1000, "duration": 30, "sent": 30000,  "name": "size_128_rabbit"},
    {"broker": "rabbit", "size": 10240,  "rate": 1000, "duration": 30, "sent": 30000,  "name": "size_10kb_rabbit"},
    {"broker": "rabbit", "size": 102400, "rate": 1000, "duration": 30, "sent": 30000,  "name": "size_100kb_rabbit"},

    {"broker": "redis", "size": 1024,   "rate": 5000,  "duration": 30, "sent": 150000, "name": "load_5000_redis"},
    {"broker": "redis", "size": 1024,   "rate": 10000, "duration": 30, "sent": 300000, "name": "load_10000_redis"},

    {"broker": "rabbit", "size": 1024,  "rate": 5000,  "duration": 30, "sent": 150000, "name": "load_5000_rabbit"},
    {"broker": "rabbit", "size": 1024,  "rate": 10000, "duration": 30, "sent": 300000, "name": "load_10000_rabbit"},
]

RAW_RESULTS_FILE = "results.csv"
FINAL_RESULTS_FILE = "results_full.csv"
REPORT_FILE = "report.md"


def run_command(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def clean_queue(broker):
    print(f"[CLEAN] {broker}")
    result = run_command(["python", "clean_queue.py", "--broker", broker])
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError(f"Ошибка очистки очереди для {broker}")


def run_test(test):
    broker = test["broker"]
    duration = str(test["duration"])
    size = str(test["size"])
    rate = str(test["rate"])

    print(f"[TEST] {test['name']}")

    clean_queue(broker)

    if os.path.exists(RAW_RESULTS_FILE):
        os.remove(RAW_RESULTS_FILE)

    consumer = subprocess.Popen([
        "python", "consumer.py",
        "--broker", broker,
        "--duration", duration,
        "--result-file", RAW_RESULTS_FILE
    ])

    time.sleep(2)

    producer_result = run_command([
        "python", "producer.py",
        "--broker", broker,
        "--rate", rate,
        "--size", size,
        "--duration", duration
    ])

    print(producer_result.stdout)
    if producer_result.returncode != 0:
        print(producer_result.stderr)

    consumer.wait()

    return producer_result.stdout


def read_last_result():
    with open(RAW_RESULTS_FILE, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[-1]


def save_full_results(results):
    with open(FINAL_RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "test_name",
                "broker",
                "queue",
                "size_bytes",
                "rate_target",
                "sent",
                "duration_sec",
                "received",
                "errors",
                "real_msg_per_sec",
                "avg_latency_ms",
                "p95_latency_ms",
                "max_latency_ms"
            ]
        )
        writer.writeheader()
        writer.writerows(results)


def generate_report(results):
    lines = []
    lines.append("# СРАВНЕНИЕ RABBITMQ И REDIS\n")
    lines.append("## Автоматически собранные результаты\n")

    lines.append("| Test | Broker | Size | Rate target | Sent | Received | Real rate | Avg latency |")
    lines.append("|------|--------|------|-------------|------|----------|-----------|-------------|")

    for row in results:
        lines.append(
            f"| {row['test_name']} | {row['broker']} | {row['size_bytes']} | "
            f"{row['rate_target']} | {row['sent']} | {row['received']} | "
            f"{row['real_msg_per_sec']} | {row['avg_latency_ms']} |"
        )

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    all_results = []

    for test in TESTS:
        run_test(test)
        row = read_last_result()

        full_row = {
            "test_name": test["name"],
            "broker": row["broker"],
            "queue": row["queue"],
            "size_bytes": test["size"],
            "rate_target": test["rate"],
            "sent": test["sent"],
            "duration_sec": row["duration_sec"],
            "received": row["received"],
            "errors": row["errors"],
            "real_msg_per_sec": row["real_msg_per_sec"],
            "avg_latency_ms": row["avg_latency_ms"],
            "p95_latency_ms": row["p95_latency_ms"],
            "max_latency_ms": row["max_latency_ms"],
        }
        all_results.append(full_row)

    save_full_results(all_results)
    generate_report(all_results)

    print(f"Готово: {FINAL_RESULTS_FILE}, {REPORT_FILE}")


if __name__ == "__main__":
    main()