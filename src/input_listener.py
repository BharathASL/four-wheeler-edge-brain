"""Input listener interfaces for Phase-1.

Separates command input concerns from orchestration logic so future backends
(STT, sockets, HTTP) can reuse the same contract.
"""
from typing import Callable, Optional

from src.audio_adapter import AudioAdapter, SpeechToTextAdapter
from src.config import RobotConfig as _cfg


class InputListener:
    def poll_once(self) -> Optional[str]:
        """Return one command string, or None if there is no command."""
        raise NotImplementedError()

    def take_error(self) -> Optional[str]:
        """Return one pending listener error and clear it, if any."""
        return None


class ConsoleInputListener(InputListener):
    def __init__(self, prompt: str = "> "):
        self.prompt = prompt

    def poll_once(self) -> Optional[str]:
        try:
            raw = input(self.prompt)
        except EOFError:
            return "exit"
        text = raw.strip()
        if not text:
            return None
        return text

    def listen_forever(self, on_command: Callable[[str], None]) -> None:
        """Read commands indefinitely and forward them to a callback."""
        while True:
            cmd = self.poll_once()
            if cmd is None:
                continue
            on_command(cmd)


class SpeechInputListener(InputListener):
    def __init__(self, audio_adapter: AudioAdapter, stt_adapter: SpeechToTextAdapter, duration: float = _cfg.AUDIO_RECORD_DURATION_S):
        self.audio_adapter = audio_adapter
        self.stt_adapter = stt_adapter
        self.duration = duration
        self._pending_error: Optional[str] = None

    def poll_once(self) -> Optional[str]:
        try:
            audio_data = self.audio_adapter.record(self.duration)
            text = self.stt_adapter.transcribe(audio_data).strip()
        except TimeoutError:
            self._pending_error = "STT_TIMEOUT"
            return None
        except RuntimeError:
            self._pending_error = "STT_UNAVAILABLE"
            return None
        except Exception:
            self._pending_error = "STT_ERROR"
            return None

        if not text:
            return None
        self._pending_error = None
        return text

    def take_error(self) -> Optional[str]:
        error = self._pending_error
        self._pending_error = None
        return error


__all__ = ["InputListener", "ConsoleInputListener", "SpeechInputListener"]
