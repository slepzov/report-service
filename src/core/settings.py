import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).parent.parent

e = os.environ.get


def get_env_path() -> Optional[Path]:
    _path = (
        (BASE_DIR / ".env.local"),
        (BASE_DIR / ".env"),
        (BASE_DIR.parent / ".env.local"),
        (BASE_DIR.parent / ".env"),
    )
    for _p in _path:
        if _p.exists():
            return _p.resolve()
    return None


class Settings(BaseSettings):
    ENVIRONMENT: str = "dev"
    LOG_LEVEL: str = "INFO"
    LOG: bool = True
    DEBUG: bool = False

    # RabbitMQ
    RABBIT_AMQP_DSN: str = "amqp://guest:guest@rabbitmq:5672"
    RABBIT_AMQP_EXCHANGE: str = "amq.direct"
    RABBIT_AMQP_QUEUE_NAME_TASK_REPORT: str = "task_report"
    RABBIT_AMQP_ROUTING_KEY_TASK_REPORT: str = "task_report"
    RABBIT_AMQP_QUEUE_NAME_READY_REPORT: str = "ready_report"
    RABBIT_AMQP_ROUTING_KEY_READY_REPORT: str = "ready_report"

    class Config:
        env_file = get_env_path()


settings = Settings()
