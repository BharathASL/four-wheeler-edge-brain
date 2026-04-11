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
MOTOR_ADAPTER_MODE              str   "none"                       "none"|"mock"
MOTOR_PWM_FREQ_HZ               int   1000                         PWM frequency in Hz (clamp 1-50000)
MOTOR_MAX_DUTY_CYCLE            float 1.0                          max normalized duty cycle (clamp 0.0-1.0)
MOTOR_DEADBAND_PCT              float 0.05                         min duty threshold for stiction (clamp 0.0-0.5)
MOTOR_SPEED_TO_DUTY_LINEAR      float 1.0                          linear m/s to duty scaling (clamp 0.01-10.0)
MOTOR_SPEED_TO_DUTY_ANGULAR     float 1.0                          angular deg/s to duty scaling (clamp 0.01-10.0)
MOTOR_RAMP_TIME_S               float 0.1                          velocity ramp duration in seconds (clamp 0.0-5.0)
STT_MODE                        str   "console"                    "console"|"vosk"
VOSK_MODEL_PATH                 str   ""                           path to Vosk model directory
STT_SAMPLE_RATE_HZ              int   16000                        input sample rate for STT
STT_MAX_RETRIES                 int   2                            retry attempts after first failure
STT_RETRY_BACKOFF_S             float 0.3                          retry delay in seconds
AUDIO_PREPROCESS_ENABLED        bool  False                        "1"|"true"|"yes" to enable preprocessing
AUDIO_NOISE_GATE_ENABLED        bool  True                         "1"|"true"|"yes" to enable noise gate
AUDIO_NOISE_GATE_THRESHOLD_DBFS float -45.0                        RMS gate threshold in dBFS (clamp -60 to -10)
AUDIO_AGC_ENABLED               bool  True                         "1"|"true"|"yes" to enable AGC
AUDIO_AGC_TARGET_DBFS           float -20.0                        AGC target RMS level in dBFS (clamp -40 to -3)
AUDIO_AGC_MAX_GAIN_DB           float 24.0                         AGC max amplification cap in dB (clamp 0 to 40)
AUDIO_VAD_ENABLED               bool  True                         "1"|"true"|"yes" to enable energy VAD
AUDIO_VAD_ENERGY_THRESHOLD_DBFS float -45.0                        per-frame RMS threshold in dBFS (clamp -60 to -10)
AUDIO_VAD_FRAME_MS              int   30                           VAD frame length ms; rounded to nearest {10, 20, 30}
AUDIO_VAD_PADDING_MS            int   300                          silence padding around voice segments ms (clamp 0-2000)
AUDIO_VAD_STREAM_ENABLED        bool  False                        "1"|"true"|"yes" to enable streaming VAD capture
AUDIO_VAD_AGGRESSIVENESS        int   2                            webrtcvad aggressiveness level (clamp 0-3)
AUDIO_VAD_CHUNK_MS              int   20                           streaming VAD frame length ms; rounded to nearest {10, 20, 30}
AUDIO_VAD_SILENCE_PADDING_MS    int   400                          trailing silence before returning utterance ms (clamp 0-5000)
AUDIO_VAD_MAX_DURATION_S        float 8.0                          max utterance duration in seconds (clamp 1.0-60.0)
AUDIO_VAD_MIN_SPEECH_MS         int   100                          minimum buffered speech duration ms (clamp 0-2000)
AUDIO_VAD_SPEECH_GATE_DBFS      float -38.0                        min dBFS to start SILENCE→SPEECH transition (clamp -96 to 0)
TELEMETRY_LOG_DIR               str   "data/logs"
TELEMETRY_LOG_MAX_BYTES         int   1048576
TELEMETRY_LOG_BACKUP_COUNT      int   3
TELEMETRY_DISABLE_FILE_LOGGING  bool  False                        "1"|"true"|"yes" to disable
HTTP_API_ENABLED                bool  False                        "1"|"true"|"yes" to enable
HTTP_API_HOST                   str   "127.0.0.1"                 bind host
HTTP_API_PORT                   int   8080                        bind port
"""
from __future__ import annotations

import os
from dataclasses import dataclass, replace


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


def _clamp_vad_frame_ms(val: int) -> int:
    """Round *val* to the nearest valid VAD frame length: 10, 20, or 30 ms."""
    valid = (10, 20, 30)
    return min(valid, key=lambda v: abs(v - val))


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

    # ── Mobility adapter/calibration (Phase 2 software foundation) ─────────
    MOTOR_ADAPTER_MODE: str = "none"
    MOTOR_PWM_FREQ_HZ: int = 1000
    MOTOR_MAX_DUTY_CYCLE: float = 1.0
    MOTOR_DEADBAND_PCT: float = 0.05
    MOTOR_SPEED_TO_DUTY_LINEAR: float = 1.0
    MOTOR_SPEED_TO_DUTY_ANGULAR: float = 1.0
    MOTOR_RAMP_TIME_S: float = 0.1

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
    STT_MODE: str = "console"
    VOSK_MODEL_PATH: str = ""
    STT_SAMPLE_RATE_HZ: int = 16_000
    STT_MAX_RETRIES: int = 2
    STT_RETRY_BACKOFF_S: float = 0.3

    # STT confidence threshold and fallback
    STT_CONFIDENCE_THRESHOLD: float = 0.7  # Minimum confidence to accept transcript
    STT_REPROMPT_ON_REJECT: bool = True    # If True, re-prompt user on low confidence

    # ── Audio Preprocessing (VAD, Noise Gate, AGC) ────────────────────────────
    AUDIO_PREPROCESS_ENABLED: bool = False
    AUDIO_NOISE_GATE_ENABLED: bool = True
    AUDIO_NOISE_GATE_THRESHOLD_DBFS: float = -45.0
    AUDIO_AGC_ENABLED: bool = True
    AUDIO_AGC_TARGET_DBFS: float = -20.0
    AUDIO_AGC_MAX_GAIN_DB: float = 24.0
    AUDIO_VAD_ENABLED: bool = True
    AUDIO_VAD_ENERGY_THRESHOLD_DBFS: float = -45.0
    AUDIO_VAD_FRAME_MS: int = 30
    AUDIO_VAD_PADDING_MS: int = 300

    # ── Streaming VAD Capture (Phase 4.1) ─────────────────────────────────────
    AUDIO_VAD_STREAM_ENABLED: bool = False   # replace fixed recorder with streaming VAD
    AUDIO_VAD_AGGRESSIVENESS: int = 2        # webrtcvad aggressiveness 0-3
    AUDIO_VAD_CHUNK_MS: int = 20             # streaming frame size (10 / 20 / 30 ms)
    AUDIO_VAD_SILENCE_PADDING_MS: int = 400  # ms of silence to wait before returning
    AUDIO_VAD_MAX_DURATION_S: float = 8.0   # hard ceiling per utterance
    AUDIO_VAD_MIN_SPEECH_MS: int = 100       # discard fragments shorter than this
    AUDIO_VAD_SPEECH_GATE_DBFS: float = -38.0  # min dBFS to trigger SILENCE→SPEECH transition

    # ── Telemetry ─────────────────────────────────────────────────────────────
    LOG_DIR: str = "data/logs"
    LOG_MAX_BYTES: int = 1_048_576
    LOG_BACKUP_COUNT: int = 3
    DISABLE_FILE_LOGGING: bool = False

    # ── HTTP API ─────────────────────────────────────────────────────────────
    HTTP_API_ENABLED: bool = False
    HTTP_API_HOST: str = "127.0.0.1"
    HTTP_API_PORT: int = 8080

    # ── Model / Memory paths ──────────────────────────────────────────────────
    MODEL_MODE: str = "mock"
    MODEL_PATH: str = ""
    LLAMA_LIB_PATH: str = ""
    MEMORY_DB_PATH: str = "data/conversations.sqlite"
    MEMORY_RETRIEVAL_MODE: str = "fts"
    SEMANTIC_BACKEND: str = "auto"

    # ── Autonomy Modes ────────────────────────────────────────────────────────
    # Allowed modes: AUTONOMOUS, ASSISTED, MANUAL, SAFE_STOP
    # If an invalid mode is specified via the environment, it safely falls back to SAFE_STOP.
    OPERATING_MODE: str = "AUTONOMOUS"

    # ── Chat / Retrieval window ───────────────────────────────────────────────
    CHAT_HISTORY_TURNS: int = 4
    RETRIEVAL_TURNS: int = 3

    @classmethod
    def from_env(cls) -> "RobotConfig":
        """Build a RobotConfig from environment variables.

        Only fields that have corresponding environment variables are read from
        the environment. All other fields keep their dataclass defaults, so the
        source of truth for every constant is exactly one place.
        """
        defaults = cls()
        return replace(
            defaults,
            MODEL_TIMEOUT_S=_env_float("MODEL_TIMEOUT_S", defaults.MODEL_TIMEOUT_S),
            MODEL_COOLDOWN_S=_env_float("MODEL_COOLDOWN_SECONDS", defaults.MODEL_COOLDOWN_S),
            MOTOR_ADAPTER_MODE=_env_str("MOTOR_ADAPTER_MODE", defaults.MOTOR_ADAPTER_MODE),
            MOTOR_PWM_FREQ_HZ=max(1, min(50_000, _env_int("MOTOR_PWM_FREQ_HZ", defaults.MOTOR_PWM_FREQ_HZ))),
            MOTOR_MAX_DUTY_CYCLE=max(
                0.0, min(1.0, _env_float("MOTOR_MAX_DUTY_CYCLE", defaults.MOTOR_MAX_DUTY_CYCLE))
            ),
            MOTOR_DEADBAND_PCT=max(
                0.0, min(0.5, _env_float("MOTOR_DEADBAND_PCT", defaults.MOTOR_DEADBAND_PCT))
            ),
            MOTOR_SPEED_TO_DUTY_LINEAR=max(
                0.01, min(10.0, _env_float("MOTOR_SPEED_TO_DUTY_LINEAR", defaults.MOTOR_SPEED_TO_DUTY_LINEAR))
            ),
            MOTOR_SPEED_TO_DUTY_ANGULAR=max(
                0.01, min(10.0, _env_float("MOTOR_SPEED_TO_DUTY_ANGULAR", defaults.MOTOR_SPEED_TO_DUTY_ANGULAR))
            ),
            MOTOR_RAMP_TIME_S=max(0.0, min(5.0, _env_float("MOTOR_RAMP_TIME_S", defaults.MOTOR_RAMP_TIME_S))),
            STT_MODE=_env_str("STT_MODE", defaults.STT_MODE),
            VOSK_MODEL_PATH=_env_str("VOSK_MODEL_PATH", defaults.VOSK_MODEL_PATH),
            STT_SAMPLE_RATE_HZ=max(1, _env_int("STT_SAMPLE_RATE_HZ", defaults.STT_SAMPLE_RATE_HZ)),
            STT_MAX_RETRIES=max(0, _env_int("STT_MAX_RETRIES", defaults.STT_MAX_RETRIES)),
            STT_RETRY_BACKOFF_S=max(0.0, _env_float("STT_RETRY_BACKOFF_S", defaults.STT_RETRY_BACKOFF_S)),
            LOG_DIR=_env_str("TELEMETRY_LOG_DIR", defaults.LOG_DIR),
            LOG_MAX_BYTES=_env_int("TELEMETRY_LOG_MAX_BYTES", defaults.LOG_MAX_BYTES),
            LOG_BACKUP_COUNT=_env_int("TELEMETRY_LOG_BACKUP_COUNT", defaults.LOG_BACKUP_COUNT),
            DISABLE_FILE_LOGGING=_env_bool("TELEMETRY_DISABLE_FILE_LOGGING", defaults.DISABLE_FILE_LOGGING),
            HTTP_API_ENABLED=_env_bool("HTTP_API_ENABLED", defaults.HTTP_API_ENABLED),
            HTTP_API_HOST=_env_str("HTTP_API_HOST", defaults.HTTP_API_HOST),
            HTTP_API_PORT=max(1, _env_int("HTTP_API_PORT", defaults.HTTP_API_PORT)),
            MODEL_MODE=_env_str("MODEL_MODE", defaults.MODEL_MODE),
            MODEL_PATH=_env_str("MODEL_PATH", defaults.MODEL_PATH),
            LLAMA_LIB_PATH=_env_str("LLAMA_LIB_PATH", defaults.LLAMA_LIB_PATH),
            MEMORY_DB_PATH=_env_str("MEMORY_DB_PATH", defaults.MEMORY_DB_PATH),
            MEMORY_RETRIEVAL_MODE=_env_str("MEMORY_RETRIEVAL_MODE", defaults.MEMORY_RETRIEVAL_MODE),
            SEMANTIC_BACKEND=_env_str("SEMANTIC_BACKEND", defaults.SEMANTIC_BACKEND),
            STT_CONFIDENCE_THRESHOLD=min(
                1.0,
                max(0.0, _env_float("STT_CONFIDENCE_THRESHOLD", defaults.STT_CONFIDENCE_THRESHOLD)),
            ),
            STT_REPROMPT_ON_REJECT=_env_bool("STT_REPROMPT_ON_REJECT", defaults.STT_REPROMPT_ON_REJECT),
            AUDIO_PREPROCESS_ENABLED=_env_bool(
                "AUDIO_PREPROCESS_ENABLED", defaults.AUDIO_PREPROCESS_ENABLED
            ),
            AUDIO_NOISE_GATE_ENABLED=_env_bool(
                "AUDIO_NOISE_GATE_ENABLED", defaults.AUDIO_NOISE_GATE_ENABLED
            ),
            AUDIO_NOISE_GATE_THRESHOLD_DBFS=max(
                -60.0,
                min(-10.0, _env_float("AUDIO_NOISE_GATE_THRESHOLD_DBFS", defaults.AUDIO_NOISE_GATE_THRESHOLD_DBFS)),
            ),
            AUDIO_AGC_ENABLED=_env_bool("AUDIO_AGC_ENABLED", defaults.AUDIO_AGC_ENABLED),
            AUDIO_AGC_TARGET_DBFS=max(
                -40.0,
                min(-3.0, _env_float("AUDIO_AGC_TARGET_DBFS", defaults.AUDIO_AGC_TARGET_DBFS)),
            ),
            AUDIO_AGC_MAX_GAIN_DB=max(
                0.0,
                min(40.0, _env_float("AUDIO_AGC_MAX_GAIN_DB", defaults.AUDIO_AGC_MAX_GAIN_DB)),
            ),
            AUDIO_VAD_ENABLED=_env_bool("AUDIO_VAD_ENABLED", defaults.AUDIO_VAD_ENABLED),
            AUDIO_VAD_ENERGY_THRESHOLD_DBFS=max(
                -60.0,
                min(-10.0, _env_float("AUDIO_VAD_ENERGY_THRESHOLD_DBFS", defaults.AUDIO_VAD_ENERGY_THRESHOLD_DBFS)),
            ),
            AUDIO_VAD_FRAME_MS=_clamp_vad_frame_ms(
                _env_int("AUDIO_VAD_FRAME_MS", defaults.AUDIO_VAD_FRAME_MS)
            ),
            AUDIO_VAD_PADDING_MS=max(
                0, min(2000, _env_int("AUDIO_VAD_PADDING_MS", defaults.AUDIO_VAD_PADDING_MS))
            ),
            AUDIO_VAD_STREAM_ENABLED=_env_bool(
                "AUDIO_VAD_STREAM_ENABLED", defaults.AUDIO_VAD_STREAM_ENABLED
            ),
            AUDIO_VAD_AGGRESSIVENESS=max(
                0, min(3, _env_int("AUDIO_VAD_AGGRESSIVENESS", defaults.AUDIO_VAD_AGGRESSIVENESS))
            ),
            AUDIO_VAD_CHUNK_MS=_clamp_vad_frame_ms(
                _env_int("AUDIO_VAD_CHUNK_MS", defaults.AUDIO_VAD_CHUNK_MS)
            ),
            AUDIO_VAD_SILENCE_PADDING_MS=max(
                0, min(5000, _env_int("AUDIO_VAD_SILENCE_PADDING_MS", defaults.AUDIO_VAD_SILENCE_PADDING_MS))
            ),
            AUDIO_VAD_MAX_DURATION_S=max(
                1.0, min(60.0, _env_float("AUDIO_VAD_MAX_DURATION_S", defaults.AUDIO_VAD_MAX_DURATION_S))
            ),
            AUDIO_VAD_MIN_SPEECH_MS=max(
                0, min(2000, _env_int("AUDIO_VAD_MIN_SPEECH_MS", defaults.AUDIO_VAD_MIN_SPEECH_MS))
            ),
            AUDIO_VAD_SPEECH_GATE_DBFS=float(
                max(-96.0, min(0.0, _env_float("AUDIO_VAD_SPEECH_GATE_DBFS", defaults.AUDIO_VAD_SPEECH_GATE_DBFS)))
            ),
            OPERATING_MODE=_env_str("OPERATING_MODE", defaults.OPERATING_MODE).upper() if _env_str("OPERATING_MODE", "").upper() in ("AUTONOMOUS", "ASSISTED", "MANUAL", "SAFE_STOP") else "SAFE_STOP" if _env_str("OPERATING_MODE", "") else defaults.OPERATING_MODE,
        )


__all__ = ["RobotConfig"]
