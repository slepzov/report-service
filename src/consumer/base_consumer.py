import asyncio
import json
from abc import ABC, abstractmethod

from aio_pika import (
    Message,
    RobustChannel,
    RobustConnection,
    RobustExchange,
    RobustQueue,
    connect_robust,
)
from aio_pika.exchange import ExchangeType
from aio_pika.message import IncomingMessage
from structlog import get_logger


class MessageProcessingError(Exception):
    def __init__(self, msg=""):
        self.msg = msg


class BaseConsumer(ABC):
    MAX_RETRY = 5

    def __init__(
        self,
        url: str,
        amqp_queue_name: str,
        exchange_name: str,
        routing_keys: list[str],
        prefetch_count: int = 5,
        logger=None,
        loop=None,
    ):
        self.loop = loop or asyncio.get_running_loop()
        self.logger = logger or get_logger(__name__)

        self.url = url
        self.routing_keys = routing_keys
        self.exchange_name = exchange_name
        self.amqp_queue_name = amqp_queue_name
        self.prefetch_count = prefetch_count

        self.connection: RobustConnection | None = None
        self.channel: RobustChannel | None = None
        self.exchange: RobustExchange | None = None
        self.queue: RobustQueue | None = None
        self.shutdown_event = asyncio.Event()

    async def _connect(self) -> None:
        self.connection = await connect_robust(
            self.url,
            loop=self.loop,
            timeout=20,
        )

        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(
            self.exchange_name, type=ExchangeType.DIRECT, durable=True
        )

        self.queue = await self.channel.declare_queue(
            self.amqp_queue_name, durable=True
        )
        for routing_key in self.routing_keys:
            await self.queue.bind(self.exchange, routing_key=routing_key)

    async def consume(self) -> None:
        await self.queue.consume(self._process_message_wrapper)

    async def run(self) -> None:
        try:
            await self._connect()
            self.logger.info("Consumer connected and ready to consume messages.")
            await self.consume()
            shutdown_event = asyncio.Event()
            await shutdown_event.wait()
        except Exception as exp:
            self.logger.error(f"Error in consumer run loop: {exp}")
            if self.connection:
                await self.connection.close()
            raise

    async def _process_message_wrapper(self, message: IncomingMessage) -> None:
        try:
            self.logger.info("New message")
            await self.process_message(message)
        except MessageProcessingError as msg_exp:
            body = json.loads(message.body.decode("utf-8"))
            retry = body.get("retry", 0)

            if retry < self.MAX_RETRY:
                new_message = {**body, **{"retry": retry + 1}}
                await self.exchange.publish(
                    Message(body=json.dumps(new_message).encode()),
                    routing_key=message.routing_key,
                )
            elif retry == self.MAX_RETRY:
                self.logger.error(msg_exp)
                await asyncio.sleep(600)

            await message.ack()

        except NotImplementedError:
            raise

    @abstractmethod
    async def process_message(self, message: IncomingMessage) -> None:
        raise NotImplementedError("Method must be implemented")
