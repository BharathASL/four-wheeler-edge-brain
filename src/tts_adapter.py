"""TTS adapter: real and mock implementations.

Keeps speech output behind a small interface so simulation, tests, and future
hardware integrations can swap backends safely.
"""
from typing import Optional


class TTSAdapter:
    def speak(self, text: str) -> None:
        """Speak text to the output device."""
        raise NotImplementedError()


class Pyttsx3TTSAdapter(TTSAdapter):
    """pyttsx3-based offline TTS adapter.

    If the runtime cannot initialize, this adapter raises RuntimeError.
    """

    def __init__(self, rate: Optional[int] = None, volume: Optional[float] = None):
        try:
            import pyttsx3  # type: ignore
        except Exception as exc:
            raise RuntimeError("pyttsx3 is not available") from exc

        self._engine = pyttsx3.init()
        if rate is not None:
            self._engine.setProperty("rate", rate)
        if volume is not None:
            self._engine.setProperty("volume", volume)

    def speak(self, text: str) -> None:
        if not text:
            return
        self._engine.say(text)
        self._engine.runAndWait()


class MockTTSAdapter(TTSAdapter):
    """Mock adapter for unit tests and no-audio environments."""

    def __init__(self):
        self.spoken_texts = []

    def speak(self, text: str) -> None:
        self.spoken_texts.append(text)


__all__ = ["TTSAdapter", "Pyttsx3TTSAdapter", "MockTTSAdapter"]
