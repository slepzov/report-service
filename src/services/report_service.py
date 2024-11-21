import asyncio
import json
import time

import ijson
from aio_pika import Message, connect_robust
from core.settings import settings
from services.cache_repository import cache_repo
from structlog import get_logger


class ReportService:
    def __init__(self):
        self.logger = get_logger()
        self.max_retries = 3
        self.delay = 0.1
        self.cache_repo = cache_repo

    def _process_record(self, record: dict, phones: set, results: dict) -> None:
        """
        Обработка отдельной записи из большого JSON.
        """
        phone = record["phone"]
        if phone not in phones:
            return

        duration = (record["end_date"] - record["start_date"]) / 1000
        price = duration * 10

        phone_stats = results[phone]
        phone_stats["cnt_all_attempts"] += 1
        if duration <= 10:
            phone_stats["cnt_att_dur"]["10_sec"] += 1
        elif 10 < duration <= 30:
            phone_stats["cnt_att_dur"]["10_30_sec"] += 1
        else:
            phone_stats["cnt_att_dur"]["30_sec"] += 1

        phone_stats["min_price_att"] = min(phone_stats["min_price_att"], price)
        phone_stats["max_price_att"] = max(phone_stats["max_price_att"], price)
        phone_stats["total_durations"] += duration
        if duration > 15:
            phone_stats["total_prices_over_15"] += price

    def process_report(self, task: dict, task_received_time: str) -> dict:
        """
        Основной метод обработки сообщения и сбора статистики.
        """
        start_time = time.time()
        phones = set(task["phones"])

        results = {
            phone: {
                "cnt_all_attempts": 0,
                "cnt_att_dur": {"10_sec": 0, "10_30_sec": 0, "30_sec": 0},
                "min_price_att": float("inf"),
                "max_price_att": float("-inf"),
                "total_durations": 0,
                "total_prices_over_15": 0,
            }
            for phone in phones
        }

        # Проверяем номера в кеше
        missing_phones = set()
        for phone in phones:
            cached_data = self.cache_repo.get(phone)
            if cached_data:
                results[phone] = cached_data
            else:
                missing_phones.add(phone)

        # Если все номера найдены в кеше, возвращаем результат
        if not missing_phones:
            final_results = self._format_results(results)
            total_duration = time.time() - start_time
            return self._prepare_response(
                task, task_received_time, final_results, total_duration
            )

        # Открываем файл и обрабатываем недостающие номера
        with open("data/data.json", "r") as f:
            for record in ijson.items(f, "item"):
                if record["phone"] in missing_phones:
                    self._process_record(record, missing_phones, results)

        # Сохраняем недостающие данные в кеш
        for phone in missing_phones:
            self.cache_repo.save(phone, results[phone])

        # Формируем результаты
        final_results = self._format_results(results)
        total_duration = time.time() - start_time
        return self._prepare_response(
            task, task_received_time, final_results, total_duration
        )

    def _format_results(self, results: dict) -> list[dict]:
        """
        Форматирует результаты для ответа.
        """
        final_results = []
        for phone, stats in results.items():
            if stats["cnt_all_attempts"] == 0:
                continue

            final_results.append(
                {
                    "phone": phone,
                    "cnt_all_attempts": stats["cnt_all_attempts"],
                    "cnt_att_dur": stats["cnt_att_dur"],
                    "min_price_att": (
                        stats["min_price_att"]
                        if stats["min_price_att"] != float("inf")
                        else 0
                    ),
                    "max_price_att": (
                        stats["max_price_att"]
                        if stats["max_price_att"] != float("-inf")
                        else 0
                    ),
                    "avg_dur_att": stats["total_durations"] / stats["cnt_all_attempts"],
                    "sum_price_att_over_15": stats["total_prices_over_15"],
                }
            )
        return final_results

    def _prepare_response(
        self,
        task: dict,
        task_received_time: str,
        final_results: list,
        total_duration: float,
    ) -> dict:
        """
        Подготавливает итоговый ответ.
        """
        return {
            "correlation_id": task["correlation_id"],
            "status": "Complete",
            "task_received": task_received_time,
            "from": "report_service",
            "to": "client",
            "data": final_results,
            "total_duration": total_duration,
        }

    async def send_report(self, report: dict) -> None:
        """
        Отправляет сформированный отчет в очередь ready_report.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                connection = await connect_robust(settings.RABBIT_AMQP_DSN)

                async with connection:
                    channel = await connection.channel()
                    queue = await channel.declare_queue(
                        settings.RABBIT_AMQP_QUEUE_NAME_READY_REPORT, durable=True
                    )
                    report_message = json.dumps(report).encode("utf-8")
                    await channel.default_exchange.publish(
                        Message(body=report_message),
                        routing_key=settings.RABBIT_AMQP_ROUTING_KEY_READY_REPORT,
                    )
                    self.logger.info(f"Report sent to queue '{queue.name}': {report}")
                    return
            except Exception as exp:
                self.logger.error(f"Attempt {attempt} failed: {exp}")
                if attempt == self.max_retries:
                    self.logger.error("Max retries reached. Failed to send report.")
                    raise
                else:
                    await asyncio.sleep(self.delay)
