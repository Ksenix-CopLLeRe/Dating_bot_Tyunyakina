import argparse
import csv
import json
import statistics
import time
import redis
import pika


def parse_message(raw: bytes):
    decoder = json.JSONDecoder()
    text = raw.decode("latin1")
    obj, _ = decoder.raw_decode(text)
    return obj


def percentile(data, p):
    if not data:
        return 0.0
    data = sorted(data)
    k = int(len(data) * p / 100)
    if k >= len(data):
        k = len(data) - 1
    return data[k]


def save_result(filename, row):
    file_exists = False
    try:
        with open(filename, "r", newline="", encoding="utf-8"):
            file_exists = True
    except FileNotFoundError:
        file_exists = False

    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "broker",
                "queue",
                "duration_sec",
                "received",
                "errors",
                "real_msg_per_sec",
                "avg_latency_ms",
                "p95_latency_ms",
                "max_latency_ms"
            ]
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def run_redis(duration, host, queue_name, result_file):
    r = redis.Redis(host=host, port=6379, decode_responses=False)

    received = 0
    errors = 0
    latencies_ms = []

    start = time.time()

    while time.time() - start < duration:
        try:
            item = r.brpop(queue_name, timeout=1)
            if not item:
                continue

            _, raw = item
            msg = parse_message(raw)
            latency_ms = (time.time() - msg["ts"]) * 1000
            latencies_ms.append(latency_ms)
            received += 1

        except Exception as e:
            errors += 1
            print(f"Consume error: {e}")

    elapsed = time.time() - start
    avg_latency = statistics.mean(latencies_ms) if latencies_ms else 0.0
    p95_latency = percentile(latencies_ms, 95)
    max_latency = max(latencies_ms) if latencies_ms else 0.0
    real_rate = received / elapsed if elapsed > 0 else 0.0

    print(f"Received: {received}")
    print(f"Errors: {errors}")
    print(f"Rate: {real_rate:.2f} msg/sec")
    print(f"Avg latency: {avg_latency:.2f} ms")
    print(f"P95 latency: {p95_latency:.2f} ms")
    print(f"Max latency: {max_latency:.2f} ms")

    save_result(result_file, {
        "broker": "redis",
        "queue": queue_name,
        "duration_sec": round(elapsed, 2),
        "received": received,
        "errors": errors,
        "real_msg_per_sec": round(real_rate, 2),
        "avg_latency_ms": round(avg_latency, 2),
        "p95_latency_ms": round(p95_latency, 2),
        "max_latency_ms": round(max_latency, 2),
    })


def run_rabbit(duration, host, queue_name, result_file):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=False)

    received = 0
    errors = 0
    latencies_ms = []
    start = time.time()

    def callback(ch, method, properties, body):
        nonlocal received, errors, latencies_ms
        try:
            msg = parse_message(body)
            latency_ms = (time.time() - msg["ts"]) * 1000
            latencies_ms.append(latency_ms)
            received += 1
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            errors += 1
            print(f"Consume error: {e}")
            ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=100)
    channel.basic_consume(queue=queue_name, on_message_callback=callback)

    while time.time() - start < duration:
        connection.process_data_events(time_limit=1)

    elapsed = time.time() - start
    avg_latency = statistics.mean(latencies_ms) if latencies_ms else 0.0
    p95_latency = percentile(latencies_ms, 95)
    max_latency = max(latencies_ms) if latencies_ms else 0.0
    real_rate = received / elapsed if elapsed > 0 else 0.0

    print(f"Received: {received}")
    print(f"Errors: {errors}")
    print(f"Rate: {real_rate:.2f} msg/sec")
    print(f"Avg latency: {avg_latency:.2f} ms")
    print(f"P95 latency: {p95_latency:.2f} ms")
    print(f"Max latency: {max_latency:.2f} ms")

    save_result(result_file, {
        "broker": "rabbit",
        "queue": queue_name,
        "duration_sec": round(elapsed, 2),
        "received": received,
        "errors": errors,
        "real_msg_per_sec": round(real_rate, 2),
        "avg_latency_ms": round(avg_latency, 2),
        "p95_latency_ms": round(p95_latency, 2),
        "max_latency_ms": round(max_latency, 2),
    })

    connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker", choices=["redis", "rabbit"], required=True)
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--queue", type=str, default="test_queue")
    parser.add_argument("--result-file", type=str, default="results.csv")

    args = parser.parse_args()

    if args.broker == "redis":
        run_redis(args.duration, args.host, args.queue, args.result_file)
    else:
        run_rabbit(args.duration, args.host, args.queue, args.result_file)

# python consumer.py --broker redis --duration 30