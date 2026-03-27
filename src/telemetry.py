"""Simple telemetry and logging helper for Phase‑1.

This module provides a lightweight wrapper around Python's `logging`.
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from src.config import RobotConfig as _cfg

DEFAULT_LOG_DIR = Path(_cfg.LOG_DIR)
DEFAULT_MAX_BYTES = _cfg.LOG_MAX_BYTES
DEFAULT_BACKUP_COUNT = _cfg.LOG_BACKUP_COUNT


def _resolve_logfile(name: str, logfile: Optional[str]) -> Optional[Path]:
    if os.getenv("TELEMETRY_DISABLE_FILE_LOGGING", "0").strip().lower() in {"1", "true", "yes"}:
        return None

    if logfile:
        path = Path(logfile)
    else:
        log_dir = Path(os.getenv("TELEMETRY_LOG_DIR", str(DEFAULT_LOG_DIR)))
        path = log_dir / f"{name}.log"

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _log_rotation_settings() -> tuple[int, int]:
    max_bytes = os.getenv("TELEMETRY_LOG_MAX_BYTES", str(DEFAULT_MAX_BYTES))
    backup_count = os.getenv("TELEMETRY_LOG_BACKUP_COUNT", str(DEFAULT_BACKUP_COUNT))
    try:
        parsed_max_bytes = max(1, int(max_bytes))
    except ValueError:
        parsed_max_bytes = DEFAULT_MAX_BYTES
    try:
        parsed_backup_count = max(1, int(backup_count))
    except ValueError:
        parsed_backup_count = DEFAULT_BACKUP_COUNT
    return parsed_max_bytes, parsed_backup_count


def init_telemetry(name: str = "four_wheeler", level: int = logging.INFO, logfile: Optional[str] = None):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        logger.addHandler(ch)
        resolved_logfile = _resolve_logfile(name, logfile)
        if resolved_logfile is not None:
            max_bytes, backup_count = _log_rotation_settings()
            fh = RotatingFileHandler(
                resolved_logfile,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            fh.setFormatter(fmt)
            logger.addHandler(fh)
    return logger


__all__ = ["init_telemetry"]
