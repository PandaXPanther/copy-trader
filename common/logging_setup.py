"""Standardized loguru config — JSON lines to file, pretty to stderr."""
from __future__ import annotations
import sys
from pathlib import Path
from loguru import logger
from .config import SETTINGS


def setup(component: str) -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level=SETTINGS.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <7}</level> | "
               f"<cyan>{component}</cyan> | <level>{{message}}</level>",
    )
    logfile = SETTINGS.log_dir / f"{component}.jsonl"
    logger.add(
        logfile,
        level=SETTINGS.log_level,
        serialize=True,
        rotation="50 MB",
        retention="30 days",
        enqueue=True,
    )
