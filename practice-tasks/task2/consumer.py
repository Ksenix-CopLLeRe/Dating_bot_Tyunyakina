import time
import argparse
import redis
import pika

class Stats:
    def __init__(self):
        self.count = 0
        self.start = time.time()

    def inc(self):
        self.count += 1

    def report(self):
        elapsed = time.time() - self.start
        print(f"Received: {self.count}")
        print(f"Rate: {self.count / elapsed:.2f} msg/sec")


def run_redis(duration):
    r = redis.Redis(host='localhost', port=6379)
    stats = Stats()
    start = time.time()

    while time.time() - start < duration:
        msg = r.brpop("queue", timeout=1)
        if msg:
            stats.inc()

    stats.report()


def run_rabbit(duration):
    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connection.channel()
    channel.queue_declare(queue="queue")

    stats = Stats()
    start = time.time()

    def callback(ch, method, properties, body):
        stats.inc()
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue="queue", on_message_callback=callback)

    while time.time() - start < duration:
        connection.process_data_events(time_limit=1)

    stats.report()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker", choices=["redis", "rabbit"], required=True)
    parser.add_argument("--duration", type=int, default=10)

    args = parser.parse_args()

    if args.broker == "redis":
        run_redis(args.duration)
    else:
        run_rabbit(args.duration)