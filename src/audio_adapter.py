"""Audio adapter: real and mock implementations.

Keep the interface minimal: `record(duration)` and `play(waveform)`.
Real adapter should wrap `sounddevice` or other backend; tests should use `MockAudioAdapter`.
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


__all__ = ["AudioAdapter", "MockAudioAdapter"]
