import logging
import os

from datetime import datetime, timezone


# Base directory
BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

# logs/seharta.log
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

import sys

def get_logger(name: str, filename: str) -> logging.Logger:
    new_logger = logging.getLogger(name)
    new_logger.setLevel(logging.INFO)
    new_logger.propagate = False
    
    if not new_logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        file_path = os.path.join(LOGS_DIR, filename)
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        new_logger.addHandler(file_handler)
        
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(formatter)
        new_logger.addHandler(stream_handler)
        
    return new_logger

# Exported loggers
app_logger = get_logger("seharta", "seharta.log")
gold_logger = get_logger("gold_pipeline", "gold_pipeline.log")

# Maintain backward compatibility for existing code that imports `logger`
logger = app_logger


# Activity Logger Helper
def log_activity(
    action: str,
    user_id: str | None = None,
    endpoint: str | None = None,
    detail: str | None = None,
    ip: str | None = None,
):

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    parts = [
        f"time={timestamp}",
        f"action={action}",
    ]

    if user_id:
        parts.append(f"user_id={user_id}")

    if endpoint:
        parts.append(f"endpoint={endpoint}")

    if ip:
        parts.append(f"ip={ip}")

    if detail:
        parts.append(f"detail={detail}")

    logger.info(" | ".join(parts))