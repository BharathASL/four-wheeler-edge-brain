"""Simple telemetry and logging helper for Phase‑1.

This module provides a lightweight wrapper around Python's `logging`.
"""
import logging
from typing import Optional


def init_telemetry(name: str = "four_wheeler", level: int = logging.INFO, logfile: Optional[str] = None):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        logger.addHandler(ch)
        if logfile:
            fh = logging.FileHandler(logfile)
            fh.setFormatter(fmt)
            logger.addHandler(fh)
    return logger


__all__ = ["init_telemetry"]
