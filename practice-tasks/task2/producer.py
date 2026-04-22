import argparse
import json
import os
import time
import redis
import pika


def make_message(msg_id: int, size: int) -> bytes:
    base = {
        "id": msg_id,
        "ts": time.time()
    }

    raw = json.dumps(base).encode("utf-8")

    if len(raw) > size:
        raise ValueError(f"Message size {size} is too small. Minimum is {len(raw)} bytes.")

    payload_size = size - len(raw)
    message = raw + os.urandom(payload_size)
    return message


class RedisProducer:
    def __init__(self, host="localhost", port=6379, queue_name="test_queue"):
        self.r = redis.Redis(host=host, port=port, decode_responses=False)
        self.queue_name = queue_name

    def send(self, message: bytes):
        self.r.lpush(self.queue_name, message)


class RabbitProducer:
    def __init__(self, host="localhost", queue_name="test_queue"):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=queue_name, durable=False)
        self.queue_name = queue_name

    def send(self, message: bytes):
        self.channel.basic_publish(exchange="", routing_key=self.queue_name, body=message)

    def close(self):
        self.connection.close()


def run_test(broker, rate: int, size: int, duration: int):
    sent = 0
    errors = 0
    start_time = time.time()
    next_send_time = start_time

    while time.time() - start_time < duration:
        try:
            msg = make_message(sent + 1, size)
            broker.send(msg)
            sent += 1
        except Exception as e:
            errors += 1
            print(f"Send error: {e}")

        next_send_time += 1.0 / rate
        sleep_time = next_send_time - time.time()
        if sleep_time > 0:
            time.sleep(sleep_time)

    print(f"Sent: {sent}")
    print(f"Errors: {errors}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker", choices=["redis", "rabbit"], required=True)
    parser.add_argument("--rate", type=int, default=1000)
    parser.add_argument("--size", type=int, default=1024)
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--queue", type=str, default="test_queue")

    args = parser.parse_args()

    if args.broker == "redis":
        broker = RedisProducer(host=args.host, queue_name=args.queue)
    else:
        broker = RabbitProducer(host=args.host, queue_name=args.queue)

    try:
        run_test(broker, args.rate, args.size, args.duration)
    finally:
        if args.broker == "rabbit":
            broker.close()

# python producer.py --broker redis --rate 1000 --size 1024 --duration 30