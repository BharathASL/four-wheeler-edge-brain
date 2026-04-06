"""Input listener interfaces for Phase-1.

Separates command input concerns from orchestration logic so future backends
(STT, sockets, HTTP) can reuse the same contract.
"""
import logging
from typing import Callable, Optional

from src.adapters.audio_adapter import AudioAdapter, SpeechToTextAdapter
from src.adapters.audio_preprocessor import AudioPreprocessor
from src.config import RobotConfig as _cfg


logger = logging.getLogger(__name__)


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
    def __init__(
        self,
        audio_adapter: AudioAdapter,
        stt_adapter: SpeechToTextAdapter,
        duration: float = _cfg.AUDIO_RECORD_DURATION_S,
        confidence_threshold: float = None,
        reprompt_on_reject: bool = None,
        preprocessor: Optional[AudioPreprocessor] = None,
    ):
        self.audio_adapter = audio_adapter
        self.stt_adapter = stt_adapter
        self.duration = duration
        self._pending_error: Optional[str] = None
        self._preprocessor = preprocessor
        self._last_confidence: Optional[float] = None
        defaults = _cfg()
        self.confidence_threshold = (
            confidence_threshold if confidence_threshold is not None else defaults.STT_CONFIDENCE_THRESHOLD
        )
        self.reprompt_on_reject = (
            reprompt_on_reject if reprompt_on_reject is not None else defaults.STT_REPROMPT_ON_REJECT
        )

    def poll_once(self) -> Optional[str]:
        try:
            audio_data = self.audio_adapter.record(self.duration)
            if self._preprocessor is not None:
                audio_data = self._preprocessor.process(audio_data)
                if not audio_data:  # None (gated) or b"" (empty after VAD)
                    return None
            stt_result = self.stt_adapter.transcribe(audio_data)
            text = stt_result.text.strip() if stt_result and stt_result.text else ""
            confidence = stt_result.confidence if stt_result else None
            self._last_confidence = confidence
            logger.debug("stt_recognized text=%r confidence=%r", text, confidence)
        except TimeoutError:
            self._pending_error = "STT_TIMEOUT"
            self._last_confidence = None
            return None
        except RuntimeError:
            self._pending_error = "STT_UNAVAILABLE"
            self._last_confidence = None
            return None
        except Exception:
            self._pending_error = "STT_ERROR"
            self._last_confidence = None
            return None

        if not text:
            self._last_confidence = None
            return None

        # Confidence gating: confidence=None is accepted by policy.
        if confidence is not None and confidence < self.confidence_threshold:
            logger.info(
                "stt_low_confidence text=%r confidence=%s threshold=%s reprompt=%s",
                text,
                confidence,
                self.confidence_threshold,
                self.reprompt_on_reject,
            )
            self._pending_error = "STT_LOW_CONFIDENCE"
            return None

        self._pending_error = None
        return text

    def get_last_confidence(self) -> Optional[float]:
        """Return the confidence from the last transcription attempt."""
        return self._last_confidence

    def take_error(self) -> Optional[str]:
        error = self._pending_error
        self._pending_error = None
        return error


__all__ = ["InputListener", "ConsoleInputListener", "SpeechInputListener"]
