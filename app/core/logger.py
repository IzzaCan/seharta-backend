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

LOG_FILE = os.path.join(LOGS_DIR, "seharta.log")


# Logger instance
logger = logging.getLogger("seharta")

logger.setLevel(logging.INFO)


# Prevent duplicate handlers
if not logger.handlers:

    # File handler
    file_handler = logging.FileHandler(
        LOG_FILE,
        encoding="utf-8"
    )

    file_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)


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