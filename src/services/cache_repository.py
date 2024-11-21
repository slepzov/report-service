import os
import pickle
import time

from structlog import get_logger


class CacheRepository:
    def __init__(self, cache_file="cache.pkl", ttl=60 * 10):
        """
        Инициализация репозитория кеша.
        :param cache_file: Путь к файлу для сохранения кеша.
        :param ttl: Время жизни записей в кеше (в секундах).
        """
        self.cache_file = cache_file
        self.ttl = ttl
        self.logger = get_logger()
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        """
        Загружает кеш из файла, если он существует.
        """
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "rb") as f:
                    cache = pickle.load(f)
                    self.logger.info(f"Cache loaded from {self.cache_file}")
                    # Удаляем устаревшие записи из кеша при загрузке
                    self._cleanup_cache(cache)
                    return cache
            except Exception as e:
                self.logger.error(f"Failed to load cache: {e}")
        return {}

    def _save_cache(self) -> None:
        """
        Сохраняет текущий кеш в файл.
        """
        try:
            with open(self.cache_file, "wb") as f:
                pickle.dump(self.cache, f)
                self.logger.info(f"Cache saved to {self.cache_file}")
        except Exception as e:
            self.logger.error(f"Failed to save cache: {e}")

    def _cleanup_cache(self, cache: dict) -> None:
        """
        Удаляет устаревшие записи из кеша.
        """
        current_time = time.time()
        keys_to_delete = [
            phone
            for phone, value in cache.items()
            if current_time - value["timestamp"] > self.ttl
        ]
        for phone in keys_to_delete:
            del cache[phone]
        if keys_to_delete:
            self.logger.info(
                f"Cache cleaned. Removed {len(keys_to_delete)} expired entries."
            )

    def get(self, phone: int) -> dict | None:
        """
        Получить данные из кеша для указанного номера телефона.
        """
        self._cleanup_cache(self.cache)
        return self.cache.get(phone, {}).get("data")

    def save(self, phone: int, data: dict) -> None:
        """
        Сохранить данные в кеш для указанного номера телефона.
        """
        self.cache[phone] = {"data": data, "timestamp": time.time()}
        self._cleanup_cache(self.cache)
        self._save_cache()


cache_repo = CacheRepository()
