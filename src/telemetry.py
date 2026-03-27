"""Simple telemetry and logging helper for Phase‑1.

This module provides a lightweight wrapper around Python's `logging`.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from src.config import RobotConfig

DEFAULT_LOG_DIR = Path(RobotConfig.LOG_DIR)
DEFAULT_MAX_BYTES = RobotConfig.LOG_MAX_BYTES
DEFAULT_BACKUP_COUNT = RobotConfig.LOG_BACKUP_COUNT


def _resolve_logfile(name: str, logfile: Optional[str], cfg: RobotConfig) -> Optional[Path]:
    if cfg.DISABLE_FILE_LOGGING:
        return None

    if logfile:
        path = Path(logfile)
    else:
        path = Path(cfg.LOG_DIR) / f"{name}.log"

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def init_telemetry(
    name: str = "four_wheeler",
    level: int = logging.INFO,
    logfile: Optional[str] = None,
    cfg: Optional[RobotConfig] = None,
):
    if cfg is None:
        cfg = RobotConfig.from_env()
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        logger.addHandler(ch)
        resolved_logfile = _resolve_logfile(name, logfile, cfg)
        if resolved_logfile is not None:
            fh = RotatingFileHandler(
                resolved_logfile,
                maxBytes=max(1, cfg.LOG_MAX_BYTES),
                backupCount=max(1, cfg.LOG_BACKUP_COUNT),
                encoding="utf-8",
            )
            fh.setFormatter(fmt)
            logger.addHandler(fh)
    return logger


__all__ = ["init_telemetry"]
