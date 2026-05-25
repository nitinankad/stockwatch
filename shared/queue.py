from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

logger = logging.getLogger(__name__)


class RabbitMQQueue:
    def __init__(self, url: str, queue_name: str) -> None:
        self._url = url
        self._queue_name = queue_name

    async def put(self, payload: dict[str, Any]) -> None:
        connection = await aio_pika.connect_robust(self._url)
        async with connection:
            channel = await connection.channel()
            await channel.declare_queue(self._queue_name, durable=True)
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=self._queue_name,
            )
        logger.debug("queue.put queue=%s", self._queue_name)

    async def consume(self) -> AsyncIterator[tuple[AbstractIncomingMessage, dict[str, Any]]]:
        """Yields (message, payload) pairs. Caller must ack or nack each message."""
        connection = await aio_pika.connect_robust(self._url)
        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=10)
            queue = await channel.declare_queue(self._queue_name, durable=True)
            async with queue.iterator() as messages:
                async for message in messages:
                    yield message, json.loads(message.body)
