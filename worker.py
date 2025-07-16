#!/usr/bin/env python3
from reddit_manager.utils.logging import setup_logging
from redis import Redis
from rq import Worker, Queue
import os
import sys

setup_logging()

url = os.getenv("REDIS_URL", "redis://localhost")
port = os.getenv("REDIS_PORT")
if port:
    redis_url = f"{url}:{port}/0"
else:
    redis_url = f"{url}/0"

conn = Redis.from_url(redis_url)

queue_names = sys.argv[1:] or ["default"]

queues = [Queue(name, connection=conn) for name in queue_names]
worker = Worker(queues, connection=conn)
worker.work()

