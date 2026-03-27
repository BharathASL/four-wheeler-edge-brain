"""Central configuration for the Four-Wheeler Robot runtime.

All runtime constants, env-var defaults, and tunable thresholds live here.
Subsystems import from this module instead of hardcoding values inline.

Usage
-----
Read the current config (env-var overrides applied):

    from src.config import RobotConfig
    cfg = RobotConfig.from_env()

Or use the dataclass defaults directly (no env lookup):

    from src.config import RobotConfig
    cfg = RobotConfig()

Environment variables
---------------------
MODEL_MODE                      str   "mock"                       "mock"|"real"
MODEL_PATH                      str   ""                           path to .gguf file
LLAMA_LIB_PATH                  str   ""                           path to libllama.so
MEMORY_DB_PATH                  str   "data/conversations.sqlite"
MEMORY_RETRIEVAL_MODE           str   "fts"                        "fts"|"semantic"|"hybrid"
SEMANTIC_BACKEND                str   "auto"                       "auto"|"in-memory"|"faiss"
MODEL_COOLDOWN_SECONDS          float 2.0                          seconds between model calls
MODEL_TIMEOUT_S                 float 5.0                          model generation timeout
TELEMETRY_LOG_DIR               str   "data/logs"
TELEMETRY_LOG_MAX_BYTES         int   1048576
TELEMETRY_LOG_BACKUP_COUNT      int   3
TELEMETRY_DISABLE_FILE_LOGGING  bool  False                        "1"|"true"|"yes" to disable
"""
from __future__ import annotations

import os
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Internal coercion helpers
# ---------------------------------------------------------------------------

def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


def _env_bool(key: str, default: bool) -> bool:
    val = os.getenv(key, "").strip().lower()
    if val in {"1", "true", "yes"}:
        return True
    if val in {"0", "false", "no"}:
        return False
    return default


def _env_str(key: str, default: str) -> str:
    return os.getenv(key, default)


# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------

@dataclass
class RobotConfig:
    """All runtime configuration for the robot.

    Field defaults represent the canonical production values.
    ``from_env()`` reads environment variables with identical defaults so
    ``RobotConfig.from_env() == RobotConfig()`` when no env vars are set.
    """

    # ── Safety ────────────────────────────────────────────────────────────────
    MAX_LINEAR_SPEED_MPS: float = 0.35
    MAX_ANGULAR_SPEED_DPS: float = 45.0
    MIN_FRONT_PROXIMITY_M: float = 0.35
    MIN_SIDE_PROXIMITY_M: float = 0.20

    # ── Motion (rule-based fallback speeds, safety-clamped by executor) ───────
    DEFAULT_FWD_SPEED_MPS: float = 0.5
    DEFAULT_BACK_SPEED_MPS: float = -0.2
    DEFAULT_TURN_LEFT_DPS: float = 60.0
    DEFAULT_TURN_RIGHT_DPS: float = -60.0

    # ── Timing / Rate-limiting ────────────────────────────────────────────────
    MODEL_TIMEOUT_S: float = 5.0
    MODEL_COOLDOWN_S: float = 2.0

    # ── Battery simulation ────────────────────────────────────────────────────
    BATTERY_TICK_S: float = 1.0
    BATTERY_DRAIN_STEP: int = 1
    BATTERY_CHARGE_STEP: int = 2
    BATTERY_LOW_THRESHOLD: int = 20
    WATCHDOG_TICK_S: float = 0.5
    WATCHDOG_TIMEOUT_S: float = 60.0

    # ── Audio ─────────────────────────────────────────────────────────────────
    AUDIO_RECORD_DURATION_S: float = 3.0

    # ── Telemetry ─────────────────────────────────────────────────────────────
    LOG_DIR: str = "data/logs"
    LOG_MAX_BYTES: int = 1_048_576
    LOG_BACKUP_COUNT: int = 3
    DISABLE_FILE_LOGGING: bool = False

    # ── Model / Memory paths ──────────────────────────────────────────────────
    MODEL_MODE: str = "mock"
    MODEL_PATH: str = ""
    LLAMA_LIB_PATH: str = ""
    MEMORY_DB_PATH: str = "data/conversations.sqlite"
    MEMORY_RETRIEVAL_MODE: str = "fts"
    SEMANTIC_BACKEND: str = "auto"

    # ── Chat / Retrieval window ───────────────────────────────────────────────
    CHAT_HISTORY_TURNS: int = 4
    RETRIEVAL_TURNS: int = 3

    @classmethod
    def from_env(cls) -> "RobotConfig":
        """Build a RobotConfig from environment variables.

        Reads the same variable names that were previously scattered across
        ``main.py`` and ``src/telemetry.py``. All defaults match the dataclass
        defaults above so that ``RobotConfig.from_env() == RobotConfig()``
        when no environment variables are set.
        """
        return cls(
            # Safety — no env-var overrides; kept at dataclass defaults.
            MAX_LINEAR_SPEED_MPS=0.35,
            MAX_ANGULAR_SPEED_DPS=45.0,
            MIN_FRONT_PROXIMITY_M=0.35,
            MIN_SIDE_PROXIMITY_M=0.20,
            # Motion — no env-var overrides; kept at dataclass defaults.
            DEFAULT_FWD_SPEED_MPS=0.5,
            DEFAULT_BACK_SPEED_MPS=-0.2,
            DEFAULT_TURN_LEFT_DPS=60.0,
            DEFAULT_TURN_RIGHT_DPS=-60.0,
            # Timing
            MODEL_TIMEOUT_S=_env_float("MODEL_TIMEOUT_S", 5.0),
            MODEL_COOLDOWN_S=_env_float("MODEL_COOLDOWN_SECONDS", 2.0),
            # Battery — no env-var overrides; kept at dataclass defaults.
            BATTERY_TICK_S=1.0,
            BATTERY_DRAIN_STEP=1,
            BATTERY_CHARGE_STEP=2,
            BATTERY_LOW_THRESHOLD=20,
            WATCHDOG_TICK_S=0.5,
            WATCHDOG_TIMEOUT_S=60.0,
            # Audio — no env-var overrides; kept at dataclass defaults.
            AUDIO_RECORD_DURATION_S=3.0,
            # Telemetry
            LOG_DIR=_env_str("TELEMETRY_LOG_DIR", "data/logs"),
            LOG_MAX_BYTES=_env_int("TELEMETRY_LOG_MAX_BYTES", 1_048_576),
            LOG_BACKUP_COUNT=_env_int("TELEMETRY_LOG_BACKUP_COUNT", 3),
            DISABLE_FILE_LOGGING=_env_bool("TELEMETRY_DISABLE_FILE_LOGGING", False),
            # Model / Memory
            MODEL_MODE=_env_str("MODEL_MODE", "mock"),
            MODEL_PATH=_env_str("MODEL_PATH", ""),
            LLAMA_LIB_PATH=_env_str("LLAMA_LIB_PATH", ""),
            MEMORY_DB_PATH=_env_str("MEMORY_DB_PATH", "data/conversations.sqlite"),
            MEMORY_RETRIEVAL_MODE=_env_str("MEMORY_RETRIEVAL_MODE", "fts"),
            SEMANTIC_BACKEND=_env_str("SEMANTIC_BACKEND", "auto"),
            # Chat — no env-var overrides; kept at dataclass defaults.
            CHAT_HISTORY_TURNS=4,
            RETRIEVAL_TURNS=3,
        )


__all__ = ["RobotConfig"]
