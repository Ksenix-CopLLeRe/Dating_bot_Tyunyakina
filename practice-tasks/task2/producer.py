import time
import threading
import argparse
import redis
import pika
import os

def create_message(size):
    return os.urandom(size)

class RedisProducer:
    def __init__(self):
        self.r = redis.Redis(host='localhost', port=6379)

    def send(self, msg):
        self.r.lpush("queue", msg)


class RabbitProducer:
    def __init__(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
        self.channel = connection.channel()
        self.channel.queue_declare(queue="queue")

    def send(self, msg):
        self.channel.basic_publish(exchange='', routing_key='queue', body=msg)


def run(producer, rate, msg_size, duration):
    interval = 1.0 / rate
    sent = 0
    start = time.time()

    while time.time() - start < duration:
        msg = create_message(msg_size)
        producer.send(msg)
        sent += 1
        time.sleep(interval)

    print(f"Sent: {sent}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker", choices=["redis", "rabbit"], required=True)
    parser.add_argument("--rate", type=int, default=1000)
    parser.add_argument("--size", type=int, default=1024)
    parser.add_argument("--duration", type=int, default=10)

    args = parser.parse_args()

    if args.broker == "redis":
        producer = RedisProducer()
    else:
        producer = RabbitProducer()

    run(producer, args.rate, args.size, args.duration)