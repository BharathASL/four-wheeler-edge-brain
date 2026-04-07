from src.config import RobotConfig


def test_build_input_listener_console_mode():
    from main import _build_input_listener

    class _Logger:
        def warning(self, *args, **kwargs):
            return None

        def info(self, *args, **kwargs):
            return None

    listener, mode = _build_input_listener(
        stt_mode="console",
        vosk_model_path="",
        cfg=RobotConfig(),
        logger=_Logger(),
    )

    assert mode == "console"
    assert listener.__class__.__name__ == "ConsoleInputListener"


def test_build_input_listener_unknown_mode_falls_back_to_console():
    from main import _build_input_listener

    class _Logger:
        def __init__(self):
            self.messages = []

        def warning(self, *args, **kwargs):
            self.messages.append(args)

        def info(self, *args, **kwargs):
            return None

    logger = _Logger()
    listener, mode = _build_input_listener(
        stt_mode="something-else",
        vosk_model_path="",
        cfg=RobotConfig(),
        logger=logger,
    )

    assert mode == "console"
    assert listener.__class__.__name__ == "ConsoleInputListener"
    assert logger.messages


def test_build_input_listener_vosk_failure_falls_back_to_console():
    from main import _build_input_listener

    class _Logger:
        def __init__(self):
            self.messages = []

        def warning(self, *args, **kwargs):
            self.messages.append(args)

        def info(self, *args, **kwargs):
            return None

    logger = _Logger()
    listener, mode = _build_input_listener(
        stt_mode="vosk",
        vosk_model_path="/path/that/does/not/exist",
        cfg=RobotConfig(),
        logger=logger,
    )

    assert mode == "console"
    assert listener.__class__.__name__ == "ConsoleInputListener"
    assert logger.messages
