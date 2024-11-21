import json
from datetime import datetime, timezone

from aio_pika.message import IncomingMessage
from core.settings import settings
from services.report_service import ReportService

from .base_consumer import BaseConsumer, MessageProcessingError


class ReportConsumer(BaseConsumer):
    def __init__(self, loop):
        consumer_settings = {
            "url": settings.RABBIT_AMQP_DSN,
            "amqp_queue_name": settings.RABBIT_AMQP_QUEUE_NAME_TASK_REPORT,
            "routing_keys": [settings.RABBIT_AMQP_ROUTING_KEY_TASK_REPORT],
            "exchange_name": settings.RABBIT_AMQP_EXCHANGE,
        }
        super().__init__(loop=loop, **consumer_settings)
        self.report_service = ReportService()

    async def process_message(self, message: IncomingMessage) -> None:
        try:
            task_received_time = datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S.%f"
            )
            body = json.loads(message.body.decode("utf-8"))
            self.logger.bind(message_body=body).info("Event received:")
            report = self.report_service.process_report(body, task_received_time)
            await self.report_service.send_report(report)
        except Exception as exp:
            self.logger.error(exp)
            raise MessageProcessingError(msg=exp)
        finally:
            await message.ack()
