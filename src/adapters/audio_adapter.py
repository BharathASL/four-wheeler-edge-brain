"""Audio and speech adapters: real and mock implementations.

Keep the interfaces minimal:
- `AudioAdapter.record(duration)` and `AudioAdapter.play(audio_data)`
- `SpeechToTextAdapter.transcribe(audio_data)`

Real adapters should wrap concrete backends; tests should use the mock adapters.
"""
from typing import Any


class AudioAdapter:
    def record(self, duration: float) -> bytes:
        """Record audio for `duration` seconds and return raw bytes."""
        raise NotImplementedError()

    def play(self, audio_data: bytes) -> None:
        """Play raw audio bytes to the default output device."""
        raise NotImplementedError()


class MockAudioAdapter(AudioAdapter):
    def __init__(self):
        self.recordings = []

    def record(self, duration: float) -> bytes:
        snippet = f"mock-audio-{duration}s".encode("utf-8")
        self.recordings.append(snippet)
        return snippet

    def play(self, audio_data: bytes) -> None:
        # No-op for tests
        return None


class SpeechToTextAdapter:
    def transcribe(self, audio_data: bytes) -> str:
        """Return the recognized text for `audio_data`."""
        raise NotImplementedError()


class MockSpeechToTextAdapter(SpeechToTextAdapter):
    def __init__(self, response: str = "mock transcription"):
        self.response = response
        self.transcriptions = []

    def transcribe(self, audio_data: bytes) -> str:
        self.transcriptions.append(audio_data)
        return self.response


__all__ = [
    "AudioAdapter",
    "MockAudioAdapter",
    "SpeechToTextAdapter",
    "MockSpeechToTextAdapter",
]
