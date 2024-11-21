import asyncio
import json

from aio_pika import Message, connect_robust

MESSAGES = [
    {"correlation_id": 13242421424214, "phones": [1, 2, 3, 3, 5, 11, 67, 45, 23, 33]},
    {"correlation_id": 13242421424215, "phones": [4, 5, 6, 4, 99, 98, 97, 56, 45, 45]},
    {"correlation_id": 13242421424216, "phones": [7, 8, 9, 10, 11, 12, 13, 14, 15, 16]},
    {
        "correlation_id": 13242421424217,
        "phones": [17, 18, 19, 20, 21, 22, 23, 24, 25, 36],
    },
    {
        "correlation_id": 13242421424218,
        "phones": [37, 38, 39, 10, 11, 32, 13, 45, 15, 16],
    },
    {"correlation_id": 13242421424219, "phones": [7, 1, 0, 10, 76, 8, 78, 15, 1, 11]},
    {
        "correlation_id": 13242421424220,
        "phones": [83, 81, 91, 11, 51, 44, 7, 15, 25, 76],
    },
    {
        "correlation_id": 13242421424221,
        "phones": [0, 58, 59, 50, 51, 52, 53, 54, 55, 36],
    },
    {"correlation_id": 13242421424222, "phones": [70, 82, 9, 3, 11, 12, 2, 75, 87, 90]},
    {
        "correlation_id": 13242421424223,
        "phones": [66, 8, 99, 55, 33, 44, 66, 77, 43, 39],
    },
]


async def send_message(channel, data):
    message_body = json.dumps(data).encode("utf-8")
    message = Message(body=message_body)

    await channel.default_exchange.publish(
        message,
        routing_key="task_report",
    )

    print("Message sent:", data)


async def main():
    connection = await connect_robust("amqp://guest:guest@localhost/")

    async with connection:
        channel = await connection.channel()
        await channel.declare_queue("task_report", durable=True)

        tasks = [send_message(channel, data) for data in MESSAGES]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
