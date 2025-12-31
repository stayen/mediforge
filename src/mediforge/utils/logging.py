"""Logging configuration."""

import logging
import os
import sys
from enum import Enum


class LogLevel(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"


LEVEL_MAP = {
    'error': logging.ERROR,
    'warning': logging.WARNING,
    'info': logging.INFO,
    'debug': logging.DEBUG,
}


def configure_logging(level: str) -> None:
    """
    Configure logging for the application.

    Args:
        level: Log level name (error, warning, info, debug)
    """
    # Check environment variable override
    env_level = os.environ.get('MEDIFORGE_LOG_LEVEL', '').lower()
    if env_level in LEVEL_MAP:
        level = env_level

    log_level = LEVEL_MAP.get(level, logging.WARNING)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s: %(message)s' if log_level >= logging.WARNING
        else '%(levelname)s [%(name)s]: %(message)s',
        stream=sys.stderr,
        force=True,  # Allow reconfiguration
    )

    # Reduce noise from third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def get_logger(name: str, level: str | None = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (typically __name__)
        level: Optional level override

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    if level:
        logger.setLevel(LEVEL_MAP.get(level, logging.WARNING))
    return logger
