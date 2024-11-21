import asyncio
import signal

from consumer.report_consumer import ReportConsumer
from core.logger import setup_logger

setup_logger()


def handle_stop_signal(consumer: ReportConsumer) -> None:
    consumer.shutdown_event.set()


def setup_signal_handlers(consumer: ReportConsumer) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_stop_signal, consumer)


async def main():
    consumer = ReportConsumer(asyncio.get_running_loop())
    setup_signal_handlers(consumer)
    await consumer.run()


if __name__ == "__main__":
    asyncio.run(main())
