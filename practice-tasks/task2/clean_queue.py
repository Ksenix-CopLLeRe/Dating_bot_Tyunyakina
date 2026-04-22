import argparse
import redis
import pika

parser = argparse.ArgumentParser()
parser.add_argument("--broker", choices=["redis", "rabbit"], required=True)
parser.add_argument("--queue", default="test_queue")
args = parser.parse_args()

if args.broker == "redis":
    r = redis.Redis(host="localhost", port=6379)
    r.delete(args.queue)
    print("Redis queue cleared")

else:
    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connection.channel()
    channel.queue_delete(queue=args.queue)
    channel.queue_declare(queue=args.queue, durable=False)
    connection.close()
    print("RabbitMQ queue cleared")


# python clean_queue.py --broker redis