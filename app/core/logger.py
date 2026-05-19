"""Logging setup via loguru.

Usage — business code imports logger directly:
    from loguru import logger

    logger.info("hello")
    logger.error("something went wrong")
"""

import os
import sys

from dotenv import load_dotenv
from loguru import logger as _logger

load_dotenv()


def setup_logging() -> None:
    """Configure loguru (call once at startup)."""
    _logger.remove()  # remove default stderr handler
    _logger.add(
        sys.stdout,
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="[{time:YYYY-MM-DD HH:mm:ss}] {level:<8} [{module}] {message}",
    )
