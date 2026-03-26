import logging
from logging.handlers import RotatingFileHandler

from src.telemetry import init_telemetry


def test_init_telemetry_adds_rotating_file_handler_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEMETRY_LOG_DIR", str(tmp_path))
    monkeypatch.delenv("TELEMETRY_DISABLE_FILE_LOGGING", raising=False)

    logger = init_telemetry("telemetry_rotation_default")

    file_handlers = [handler for handler in logger.handlers if isinstance(handler, RotatingFileHandler)]
    assert len(file_handlers) == 1
    assert file_handlers[0].baseFilename.endswith("telemetry_rotation_default.log")


def test_init_telemetry_honors_rotation_env_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEMETRY_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("TELEMETRY_LOG_MAX_BYTES", "2048")
    monkeypatch.setenv("TELEMETRY_LOG_BACKUP_COUNT", "5")

    logger = init_telemetry("telemetry_rotation_env")

    file_handler = next(handler for handler in logger.handlers if isinstance(handler, RotatingFileHandler))
    assert file_handler.maxBytes == 2048
    assert file_handler.backupCount == 5


def test_init_telemetry_can_disable_file_logging(monkeypatch):
    monkeypatch.setenv("TELEMETRY_DISABLE_FILE_LOGGING", "1")

    logger = init_telemetry("telemetry_no_file")

    assert all(not isinstance(handler, RotatingFileHandler) for handler in logger.handlers)
    assert any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers)