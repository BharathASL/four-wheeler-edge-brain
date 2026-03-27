"""Tests for src/config.py — defaults and environment variable overrides."""
import pytest

from src.config import RobotConfig


class TestRobotConfigDefaults:
    def test_safety_defaults(self):
        cfg = RobotConfig()
        assert cfg.MAX_LINEAR_SPEED_MPS == 0.35
        assert cfg.MAX_ANGULAR_SPEED_DPS == 45.0
        assert cfg.MIN_FRONT_PROXIMITY_M == 0.35
        assert cfg.MIN_SIDE_PROXIMITY_M == 0.20

    def test_motion_defaults(self):
        cfg = RobotConfig()
        assert cfg.DEFAULT_FWD_SPEED_MPS == 0.5
        assert cfg.DEFAULT_BACK_SPEED_MPS == -0.2
        assert cfg.DEFAULT_TURN_LEFT_DPS == 60.0
        assert cfg.DEFAULT_TURN_RIGHT_DPS == -60.0

    def test_timing_defaults(self):
        cfg = RobotConfig()
        assert cfg.MODEL_TIMEOUT_S == 5.0
        assert cfg.MODEL_COOLDOWN_S == 2.0

    def test_battery_defaults(self):
        cfg = RobotConfig()
        assert cfg.BATTERY_TICK_S == 1.0
        assert cfg.BATTERY_DRAIN_STEP == 1
        assert cfg.BATTERY_CHARGE_STEP == 2
        assert cfg.BATTERY_LOW_THRESHOLD == 20
        assert cfg.WATCHDOG_TICK_S == 0.5
        assert cfg.WATCHDOG_TIMEOUT_S == 60.0

    def test_audio_defaults(self):
        cfg = RobotConfig()
        assert cfg.AUDIO_RECORD_DURATION_S == 3.0

    def test_telemetry_defaults(self):
        cfg = RobotConfig()
        assert cfg.LOG_DIR == "data/logs"
        assert cfg.LOG_MAX_BYTES == 1_048_576
        assert cfg.LOG_BACKUP_COUNT == 3
        assert cfg.DISABLE_FILE_LOGGING is False

    def test_http_api_defaults(self):
        cfg = RobotConfig()
        assert cfg.HTTP_API_ENABLED is False
        assert cfg.HTTP_API_HOST == "127.0.0.1"
        assert cfg.HTTP_API_PORT == 8080

    def test_model_memory_defaults(self):
        cfg = RobotConfig()
        assert cfg.MODEL_MODE == "mock"
        assert cfg.MODEL_PATH == ""
        assert cfg.LLAMA_LIB_PATH == ""
        assert cfg.MEMORY_DB_PATH == "data/conversations.sqlite"
        assert cfg.MEMORY_RETRIEVAL_MODE == "fts"
        assert cfg.SEMANTIC_BACKEND == "auto"

    def test_chat_defaults(self):
        cfg = RobotConfig()
        assert cfg.CHAT_HISTORY_TURNS == 4
        assert cfg.RETRIEVAL_TURNS == 3


class TestRobotConfigFromEnv:
    def test_from_env_no_overrides_equals_defaults(self, monkeypatch):
        for key in [
            "MODEL_MODE", "MODEL_PATH", "LLAMA_LIB_PATH",
            "MEMORY_DB_PATH", "MEMORY_RETRIEVAL_MODE", "SEMANTIC_BACKEND",
            "MODEL_COOLDOWN_SECONDS", "MODEL_TIMEOUT_S",
            "TELEMETRY_LOG_DIR", "TELEMETRY_LOG_MAX_BYTES",
            "TELEMETRY_LOG_BACKUP_COUNT", "TELEMETRY_DISABLE_FILE_LOGGING",
            "HTTP_API_ENABLED", "HTTP_API_HOST", "HTTP_API_PORT",
        ]:
            monkeypatch.delenv(key, raising=False)
        assert RobotConfig.from_env() == RobotConfig()

    def test_env_model_mode(self, monkeypatch):
        monkeypatch.setenv("MODEL_MODE", "real")
        assert RobotConfig.from_env().MODEL_MODE == "real"

    def test_env_model_path(self, monkeypatch):
        monkeypatch.setenv("MODEL_PATH", "/path/to/model.gguf")
        assert RobotConfig.from_env().MODEL_PATH == "/path/to/model.gguf"

    def test_env_llama_lib_path(self, monkeypatch):
        monkeypatch.setenv("LLAMA_LIB_PATH", "/path/to/libllama.so")
        assert RobotConfig.from_env().LLAMA_LIB_PATH == "/path/to/libllama.so"

    def test_env_model_cooldown(self, monkeypatch):
        monkeypatch.setenv("MODEL_COOLDOWN_SECONDS", "5.0")
        assert RobotConfig.from_env().MODEL_COOLDOWN_S == 5.0

    def test_env_memory_db_path(self, monkeypatch):
        monkeypatch.setenv("MEMORY_DB_PATH", "/tmp/test.sqlite")
        assert RobotConfig.from_env().MEMORY_DB_PATH == "/tmp/test.sqlite"

    def test_env_memory_retrieval_mode(self, monkeypatch):
        monkeypatch.setenv("MEMORY_RETRIEVAL_MODE", "hybrid")
        assert RobotConfig.from_env().MEMORY_RETRIEVAL_MODE == "hybrid"

    def test_env_semantic_backend(self, monkeypatch):
        monkeypatch.setenv("SEMANTIC_BACKEND", "faiss")
        assert RobotConfig.from_env().SEMANTIC_BACKEND == "faiss"

    def test_env_telemetry_log_dir(self, monkeypatch):
        monkeypatch.setenv("TELEMETRY_LOG_DIR", "/tmp/logs")
        assert RobotConfig.from_env().LOG_DIR == "/tmp/logs"

    def test_env_log_max_bytes(self, monkeypatch):
        monkeypatch.setenv("TELEMETRY_LOG_MAX_BYTES", "2097152")
        assert RobotConfig.from_env().LOG_MAX_BYTES == 2097152

    def test_env_log_backup_count(self, monkeypatch):
        monkeypatch.setenv("TELEMETRY_LOG_BACKUP_COUNT", "5")
        assert RobotConfig.from_env().LOG_BACKUP_COUNT == 5

    def test_env_http_api_enabled(self, monkeypatch):
        monkeypatch.setenv("HTTP_API_ENABLED", "1")
        assert RobotConfig.from_env().HTTP_API_ENABLED is True

    def test_env_http_api_host(self, monkeypatch):
        monkeypatch.setenv("HTTP_API_HOST", "0.0.0.0")
        assert RobotConfig.from_env().HTTP_API_HOST == "0.0.0.0"

    def test_env_http_api_port(self, monkeypatch):
        monkeypatch.setenv("HTTP_API_PORT", "9090")
        assert RobotConfig.from_env().HTTP_API_PORT == 9090

    @pytest.mark.parametrize("val", ["1", "true", "yes", "TRUE", "YES"])
    def test_env_disable_file_logging_truthy(self, monkeypatch, val):
        monkeypatch.setenv("TELEMETRY_DISABLE_FILE_LOGGING", val)
        assert RobotConfig.from_env().DISABLE_FILE_LOGGING is True

    @pytest.mark.parametrize("val", ["0", "false", "no", "FALSE", "NO"])
    def test_env_disable_file_logging_falsy(self, monkeypatch, val):
        monkeypatch.setenv("TELEMETRY_DISABLE_FILE_LOGGING", val)
        assert RobotConfig.from_env().DISABLE_FILE_LOGGING is False


class TestRobotConfigTypeCoercion:
    def test_float_coercion_from_integer_string(self, monkeypatch):
        monkeypatch.setenv("MODEL_COOLDOWN_SECONDS", "3")
        cfg = RobotConfig.from_env()
        assert isinstance(cfg.MODEL_COOLDOWN_S, float)
        assert cfg.MODEL_COOLDOWN_S == 3.0

    def test_invalid_float_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("MODEL_COOLDOWN_SECONDS", "not_a_number")
        assert RobotConfig.from_env().MODEL_COOLDOWN_S == 2.0

    def test_invalid_int_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("TELEMETRY_LOG_BACKUP_COUNT", "not_an_int")
        assert RobotConfig.from_env().LOG_BACKUP_COUNT == 3

    def test_invalid_http_port_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("HTTP_API_PORT", "bad_port")
        assert RobotConfig.from_env().HTTP_API_PORT == 8080

    def test_bool_yes_uppercase(self, monkeypatch):
        monkeypatch.setenv("TELEMETRY_DISABLE_FILE_LOGGING", "YES")
        assert RobotConfig.from_env().DISABLE_FILE_LOGGING is True


class TestConfigIntegration:
    def test_safety_constants_match_safety_controller(self):
        """Safety constants exported by safety_controller must come from config."""
        from src.safety_controller import (
            MAX_LINEAR_SPEED_MPS,
            MAX_ANGULAR_SPEED_DPS,
            MIN_FRONT_PROXIMITY_M,
            MIN_SIDE_PROXIMITY_M,
        )
        cfg = RobotConfig()
        assert cfg.MAX_LINEAR_SPEED_MPS == MAX_LINEAR_SPEED_MPS
        assert cfg.MAX_ANGULAR_SPEED_DPS == MAX_ANGULAR_SPEED_DPS
        assert cfg.MIN_FRONT_PROXIMITY_M == MIN_FRONT_PROXIMITY_M
        assert cfg.MIN_SIDE_PROXIMITY_M == MIN_SIDE_PROXIMITY_M

    def test_telemetry_defaults_match_config(self):
        """Telemetry module-level DEFAULT_* names must match config values."""
        from src.telemetry import DEFAULT_LOG_DIR, DEFAULT_MAX_BYTES, DEFAULT_BACKUP_COUNT
        cfg = RobotConfig()
        assert str(DEFAULT_LOG_DIR) == cfg.LOG_DIR
        assert DEFAULT_MAX_BYTES == cfg.LOG_MAX_BYTES
        assert DEFAULT_BACKUP_COUNT == cfg.LOG_BACKUP_COUNT

    def test_config_import_is_pure(self):
        """Importing RobotConfig must not raise even in a clean environment."""
        import importlib
        import src.config as config_mod
        importlib.reload(config_mod)
        assert hasattr(config_mod, "RobotConfig")
