"""
Logging configuration for AncientWorld.

Provides centralized logging setup with file and console handlers.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


def setup_logger(
    name: str = "ancientworld",
    level: int = logging.INFO,
    log_dir: Optional[Path] = None,
    console: bool = True,
    file: bool = True,
) -> logging.Logger:
    """
    Set up a logger with console and file handlers.

    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (default: logs/)
        console: Enable console logging
        file: Enable file logging

    Returns:
        Configured logger instance

    Example:
        >>> logger = setup_logger("my_module", level=logging.DEBUG)
        >>> logger.info("Processing started")
        >>> logger.error("An error occurred", exc_info=True)
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    simple_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)

    # File handler
    if file:
        if log_dir is None:
            log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"{name}_{timestamp}.log"

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    If the logger hasn't been set up, returns a basic logger.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Started processing")
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Set up basic configuration if not already configured
        setup_logger(name)
    return logger


# Default logger for the package
default_logger = setup_logger("ancientworld")
