import socket

import structlog
from core.settings import settings


def add_environment(_, __, event_dict):
    event_dict["environment"] = settings.ENVIRONMENT
    event_dict["hostname"] = socket.gethostname()
    return event_dict


def setup_logger():
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            add_environment,
            structlog.processors.JSONRenderer(),
        ]
    )
    return structlog.get_logger()
