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
        assert cfg.STT_MODE == "console"
        assert cfg.VOSK_MODEL_PATH == ""
        assert cfg.STT_SAMPLE_RATE_HZ == 16000
        assert cfg.STT_MAX_RETRIES == 2
        assert cfg.STT_RETRY_BACKOFF_S == 0.3
        assert cfg.STT_CONFIDENCE_THRESHOLD == 0.7
        assert cfg.STT_REPROMPT_ON_REJECT is True

    def test_audio_preprocessing_defaults(self):
        cfg = RobotConfig()
        assert cfg.AUDIO_PREPROCESS_ENABLED is False
        assert cfg.AUDIO_NOISE_GATE_ENABLED is True
        assert cfg.AUDIO_NOISE_GATE_THRESHOLD_DBFS == -45.0
        assert cfg.AUDIO_AGC_ENABLED is True
        assert cfg.AUDIO_AGC_TARGET_DBFS == -20.0
        assert cfg.AUDIO_AGC_MAX_GAIN_DB == 24.0
        assert cfg.AUDIO_VAD_ENABLED is True
        assert cfg.AUDIO_VAD_ENERGY_THRESHOLD_DBFS == -45.0
        assert cfg.AUDIO_VAD_FRAME_MS == 30
        assert cfg.AUDIO_VAD_PADDING_MS == 300
    def test_env_stt_confidence_threshold(self, monkeypatch):
        monkeypatch.setenv("STT_CONFIDENCE_THRESHOLD", "0.42")
        assert RobotConfig.from_env().STT_CONFIDENCE_THRESHOLD == 0.42

    def test_env_stt_reprompt_on_reject(self, monkeypatch):
        monkeypatch.setenv("STT_REPROMPT_ON_REJECT", "0")
        assert RobotConfig.from_env().STT_REPROMPT_ON_REJECT is False

    def test_env_audio_preprocess_enabled(self, monkeypatch):
        monkeypatch.setenv("AUDIO_PREPROCESS_ENABLED", "1")
        assert RobotConfig.from_env().AUDIO_PREPROCESS_ENABLED is True

    def test_env_audio_noise_gate_enabled(self, monkeypatch):
        monkeypatch.setenv("AUDIO_NOISE_GATE_ENABLED", "0")
        assert RobotConfig.from_env().AUDIO_NOISE_GATE_ENABLED is False

    def test_env_audio_noise_gate_threshold(self, monkeypatch):
        monkeypatch.setenv("AUDIO_NOISE_GATE_THRESHOLD_DBFS", "-30.0")
        assert RobotConfig.from_env().AUDIO_NOISE_GATE_THRESHOLD_DBFS == -30.0

    def test_env_audio_noise_gate_threshold_clamped_high(self, monkeypatch):
        monkeypatch.setenv("AUDIO_NOISE_GATE_THRESHOLD_DBFS", "5.0")  # above -10 max
        assert RobotConfig.from_env().AUDIO_NOISE_GATE_THRESHOLD_DBFS == -10.0

    def test_env_audio_noise_gate_threshold_clamped_low(self, monkeypatch):
        monkeypatch.setenv("AUDIO_NOISE_GATE_THRESHOLD_DBFS", "-70.0")  # below -60 min
        assert RobotConfig.from_env().AUDIO_NOISE_GATE_THRESHOLD_DBFS == -60.0

    def test_env_audio_agc_enabled(self, monkeypatch):
        monkeypatch.setenv("AUDIO_AGC_ENABLED", "false")
        assert RobotConfig.from_env().AUDIO_AGC_ENABLED is False

    def test_env_audio_agc_target_dbfs_clamped(self, monkeypatch):
        monkeypatch.setenv("AUDIO_AGC_TARGET_DBFS", "0.0")  # above -3 max
        assert RobotConfig.from_env().AUDIO_AGC_TARGET_DBFS == -3.0

    def test_env_audio_agc_max_gain_clamped(self, monkeypatch):
        monkeypatch.setenv("AUDIO_AGC_MAX_GAIN_DB", "100.0")  # above 40 max
        assert RobotConfig.from_env().AUDIO_AGC_MAX_GAIN_DB == 40.0

    def test_env_audio_vad_enabled(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_ENABLED", "no")
        assert RobotConfig.from_env().AUDIO_VAD_ENABLED is False

    def test_env_audio_vad_frame_ms_valid(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_FRAME_MS", "20")
        assert RobotConfig.from_env().AUDIO_VAD_FRAME_MS == 20

    def test_env_audio_vad_frame_ms_rounds_to_nearest(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_FRAME_MS", "25")  # nearest to 20 or 30 → 30
        result = RobotConfig.from_env().AUDIO_VAD_FRAME_MS
        assert result in (20, 30)

    def test_env_audio_vad_padding_ms_clamped(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_PADDING_MS", "5000")  # above 2000 max
        assert RobotConfig.from_env().AUDIO_VAD_PADDING_MS == 2000

    def test_env_audio_vad_padding_ms_clamped_low(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_PADDING_MS", "-50")  # below 0 min
        assert RobotConfig.from_env().AUDIO_VAD_PADDING_MS == 0

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
            "STT_MODE", "VOSK_MODEL_PATH", "STT_SAMPLE_RATE_HZ", "STT_MAX_RETRIES", "STT_RETRY_BACKOFF_S",
            "STT_CONFIDENCE_THRESHOLD", "STT_REPROMPT_ON_REJECT",
            "AUDIO_PREPROCESS_ENABLED", "AUDIO_NOISE_GATE_ENABLED", "AUDIO_NOISE_GATE_THRESHOLD_DBFS",
            "AUDIO_AGC_ENABLED", "AUDIO_AGC_TARGET_DBFS", "AUDIO_AGC_MAX_GAIN_DB",
            "AUDIO_VAD_ENABLED", "AUDIO_VAD_ENERGY_THRESHOLD_DBFS", "AUDIO_VAD_FRAME_MS",
            "AUDIO_VAD_PADDING_MS",
            "TELEMETRY_LOG_DIR", "TELEMETRY_LOG_MAX_BYTES",
            "TELEMETRY_LOG_BACKUP_COUNT", "TELEMETRY_DISABLE_FILE_LOGGING",
            "HTTP_API_ENABLED", "HTTP_API_HOST", "HTTP_API_PORT",
        ]:
            monkeypatch.delenv(key, raising=False)
        assert RobotConfig.from_env() == RobotConfig()

    def test_env_stt_mode(self, monkeypatch):
        monkeypatch.setenv("STT_MODE", "vosk")
        assert RobotConfig.from_env().STT_MODE == "vosk"

    def test_env_vosk_model_path(self, monkeypatch):
        monkeypatch.setenv("VOSK_MODEL_PATH", "/tmp/vosk-model")
        assert RobotConfig.from_env().VOSK_MODEL_PATH == "/tmp/vosk-model"

    def test_env_stt_sample_rate(self, monkeypatch):
        monkeypatch.setenv("STT_SAMPLE_RATE_HZ", "8000")
        assert RobotConfig.from_env().STT_SAMPLE_RATE_HZ == 8000

    def test_env_stt_max_retries(self, monkeypatch):
        monkeypatch.setenv("STT_MAX_RETRIES", "4")
        assert RobotConfig.from_env().STT_MAX_RETRIES == 4

    def test_env_stt_retry_backoff(self, monkeypatch):
        monkeypatch.setenv("STT_RETRY_BACKOFF_S", "0.5")
        assert RobotConfig.from_env().STT_RETRY_BACKOFF_S == 0.5

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

    def test_stt_confidence_threshold_clamped_to_one(self, monkeypatch):
        monkeypatch.setenv("STT_CONFIDENCE_THRESHOLD", "1.8")
        assert RobotConfig.from_env().STT_CONFIDENCE_THRESHOLD == 1.0


class TestConfigIntegration:
    def test_safety_constants_match_config(self):
        """Safety constants exported by safety_controller must come from config."""
        from src.core.safety_controller import (
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


class TestStreamingVADConfigDefaults:
    def test_streaming_vad_defaults(self):
        cfg = RobotConfig()
        assert cfg.AUDIO_VAD_STREAM_ENABLED is False
        assert cfg.AUDIO_VAD_AGGRESSIVENESS == 2
        assert cfg.AUDIO_VAD_CHUNK_MS == 20
        assert cfg.AUDIO_VAD_SILENCE_PADDING_MS == 400
        assert cfg.AUDIO_VAD_MAX_DURATION_S == 8.0
        assert cfg.AUDIO_VAD_MIN_SPEECH_MS == 100

    def test_env_vad_stream_enabled(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_STREAM_ENABLED", "1")
        assert RobotConfig.from_env().AUDIO_VAD_STREAM_ENABLED is True

    def test_env_vad_aggressiveness(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_AGGRESSIVENESS", "3")
        assert RobotConfig.from_env().AUDIO_VAD_AGGRESSIVENESS == 3

    def test_env_vad_aggressiveness_clamped_high(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_AGGRESSIVENESS", "10")
        assert RobotConfig.from_env().AUDIO_VAD_AGGRESSIVENESS == 3

    def test_env_vad_aggressiveness_clamped_low(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_AGGRESSIVENESS", "-1")
        assert RobotConfig.from_env().AUDIO_VAD_AGGRESSIVENESS == 0

    def test_env_vad_chunk_ms_valid(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_CHUNK_MS", "10")
        assert RobotConfig.from_env().AUDIO_VAD_CHUNK_MS == 10

    def test_env_vad_chunk_ms_rounded_to_nearest(self, monkeypatch):
        # _clamp_vad_frame_ms rounds invalid values; ties pick the first nearest valid value, so 25 → 20.
        monkeypatch.setenv("AUDIO_VAD_CHUNK_MS", "25")
        assert RobotConfig.from_env().AUDIO_VAD_CHUNK_MS == 20

    def test_env_vad_silence_padding_ms(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_SILENCE_PADDING_MS", "600")
        assert RobotConfig.from_env().AUDIO_VAD_SILENCE_PADDING_MS == 600

    def test_env_vad_silence_padding_ms_clamped_high(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_SILENCE_PADDING_MS", "99999")
        assert RobotConfig.from_env().AUDIO_VAD_SILENCE_PADDING_MS == 5000

    def test_env_vad_silence_padding_ms_clamped_low(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_SILENCE_PADDING_MS", "-100")
        assert RobotConfig.from_env().AUDIO_VAD_SILENCE_PADDING_MS == 0

    def test_env_vad_max_duration_s(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_MAX_DURATION_S", "15.0")
        assert RobotConfig.from_env().AUDIO_VAD_MAX_DURATION_S == 15.0

    def test_env_vad_max_duration_s_clamped_high(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_MAX_DURATION_S", "999")
        assert RobotConfig.from_env().AUDIO_VAD_MAX_DURATION_S == 60.0

    def test_env_vad_max_duration_s_clamped_low(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_MAX_DURATION_S", "0.1")
        assert RobotConfig.from_env().AUDIO_VAD_MAX_DURATION_S == 1.0

    def test_env_vad_min_speech_ms(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_MIN_SPEECH_MS", "200")
        assert RobotConfig.from_env().AUDIO_VAD_MIN_SPEECH_MS == 200

    def test_env_vad_min_speech_ms_clamped_high(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_MIN_SPEECH_MS", "9999")
        assert RobotConfig.from_env().AUDIO_VAD_MIN_SPEECH_MS == 2000

    def test_env_vad_min_speech_ms_clamped_low(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_MIN_SPEECH_MS", "-50")
        assert RobotConfig.from_env().AUDIO_VAD_MIN_SPEECH_MS == 0

    def test_vad_speech_gate_dbfs_default(self):
        assert RobotConfig().AUDIO_VAD_SPEECH_GATE_DBFS == -38.0

    def test_env_vad_speech_gate_dbfs_override(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_SPEECH_GATE_DBFS", "-30.0")
        assert RobotConfig.from_env().AUDIO_VAD_SPEECH_GATE_DBFS == -30.0

    def test_env_vad_speech_gate_dbfs_clamped_high(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_SPEECH_GATE_DBFS", "5.0")
        assert RobotConfig.from_env().AUDIO_VAD_SPEECH_GATE_DBFS == 0.0

    def test_env_vad_speech_gate_dbfs_clamped_low(self, monkeypatch):
        monkeypatch.setenv("AUDIO_VAD_SPEECH_GATE_DBFS", "-200.0")
        assert RobotConfig.from_env().AUDIO_VAD_SPEECH_GATE_DBFS == -96.0
