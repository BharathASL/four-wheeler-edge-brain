"""Audio and speech adapters: real and mock implementations.

Keep the interfaces minimal:
- `AudioAdapter.record(duration)` and `AudioAdapter.play(audio_data)`
- `SpeechToTextAdapter.transcribe(audio_data)`

Real adapters should wrap concrete backends; tests should use the mock adapters.
"""
import json
import logging
import os
import time
from importlib import import_module
from typing import Any


logger = logging.getLogger(__name__)


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



# --- STTResult: (text, confidence) ---
class STTResult:
    def __init__(self, text: str, confidence: float | None = None):
        self.text = text
        self.confidence = confidence
    def __repr__(self):
        return f"STTResult(text={self.text!r}, confidence={self.confidence!r})"


class SpeechToTextAdapter:
    def transcribe(self, audio_data: bytes) -> STTResult:
        """Return the recognized text and confidence for `audio_data`."""
        raise NotImplementedError()


class MockSpeechToTextAdapter(SpeechToTextAdapter):
    def __init__(self, response: str = "mock transcription", confidence: float = 1.0):
        self.response = response
        self.confidence = confidence
        self.transcriptions = []

    def transcribe(self, audio_data: bytes) -> STTResult:
        self.transcriptions.append(audio_data)
        return STTResult(self.response, self.confidence)


def _load_vosk_runtime() -> Any:
    """Load and return the `vosk` runtime module.

    This is lazy so tests and non-STT paths do not require Vosk at import-time.
    """
    try:
        return import_module("vosk")
    except Exception as exc:
        raise RuntimeError("vosk runtime is unavailable") from exc


def _load_sounddevice_runtime() -> Any:
    """Load and return the `sounddevice` runtime module lazily."""
    try:
        return import_module("sounddevice")
    except Exception as exc:
        raise RuntimeError("sounddevice runtime is unavailable") from exc


class SoundDeviceAudioAdapter(AudioAdapter):
    """Audio recorder using the default input device via sounddevice.

    Returns int16 PCM bytes (mono by default), suitable for Vosk decoding.
    """

    def __init__(self, sample_rate_hz: int = 16_000, channels: int = 1):
        self.sample_rate_hz = max(1, int(sample_rate_hz))
        self.channels = max(1, int(channels))
        self._runtime = _load_sounddevice_runtime()

    def record(self, duration: float) -> bytes:
        duration = float(duration)
        if duration <= 0:
            return b""

        frames = int(self.sample_rate_hz * duration)
        try:
            recording = self._runtime.rec(
                frames,
                samplerate=self.sample_rate_hz,
                channels=self.channels,
                dtype="int16",
            )
            self._runtime.wait()
        except Exception as exc:
            raise RuntimeError("audio capture failed") from exc

        try:
            return recording.tobytes()
        except Exception as exc:
            raise RuntimeError("audio capture produced invalid buffer") from exc

    def play(self, audio_data: bytes) -> None:
        # Playback path is handled by the dedicated TTS adapter.
        return None


class VoskSpeechToTextAdapter(SpeechToTextAdapter):
    """Vosk-backed speech-to-text adapter with confidence output."""

    def __init__(
        self,
        model_path: str,
        sample_rate_hz: int = 16_000,
        max_retries: int = 2,
        retry_backoff_s: float = 0.3,
    ):
        model_path = (model_path or "").strip()
        if not model_path:
            raise RuntimeError("Vosk model path is required")
        if not os.path.exists(model_path):
            raise RuntimeError(f"Vosk model path does not exist: {model_path}")

        self.model_path = model_path
        self.sample_rate_hz = max(1, int(sample_rate_hz))
        self.max_retries = max(0, int(max_retries))
        self.retry_backoff_s = max(0.0, float(retry_backoff_s))

        runtime = _load_vosk_runtime()
        model_cls = getattr(runtime, "Model", None)
        if model_cls is None:
            raise RuntimeError("vosk runtime missing Model class")

        self._runtime = runtime
        try:
            self._model = model_cls(self.model_path)
        except Exception as exc:
            raise RuntimeError("failed to load Vosk model") from exc

    def _decode_once(self, audio_data: bytes) -> STTResult:
        recognizer_cls = getattr(self._runtime, "KaldiRecognizer", None)
        if recognizer_cls is None:
            raise RuntimeError("vosk runtime missing KaldiRecognizer class")

        recognizer = recognizer_cls(self._model, self.sample_rate_hz)
        accepted = recognizer.AcceptWaveform(audio_data)
        result_payload = recognizer.Result()
        final_payload = recognizer.FinalResult()
        if accepted:
            payload = result_payload
        else:
            payload = final_payload

        try:
            parsed = json.loads(payload or "{}")
        except Exception:
            logger.warning("vosk_payload_parse_failed payload=%r", payload)
            return STTResult("", None)
        text = str(parsed.get("text", "")).strip()
        # Vosk may provide a 'confidence' field or a 'result' list with word-level confidences
        conf = parsed.get("confidence")
        if conf is None and "result" in parsed:
            words = parsed["result"]
            if isinstance(words, list) and words:
                confs = [w.get("conf", 1.0) for w in words if "conf" in w]
                if confs:
                    conf = sum(confs) / len(confs)
        try:
            conf = float(conf) if conf is not None else None
        except (TypeError, ValueError):
            logger.warning("vosk_confidence_parse_failed confidence=%r", conf)
            conf = None
        return STTResult(text, conf)

    def transcribe(self, audio_data: bytes) -> STTResult:
        if not isinstance(audio_data, (bytes, bytearray)):
            raise RuntimeError("audio_data must be bytes")
        if not audio_data:
            return STTResult("", None)

        attempts = self.max_retries + 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                return self._decode_once(bytes(audio_data))
            except Exception as exc:
                last_error = exc
                if attempt < attempts - 1 and self.retry_backoff_s > 0.0:
                    time.sleep(self.retry_backoff_s)
        raise RuntimeError("Vosk transcription failed") from last_error


__all__ = [
    "AudioAdapter",
    "MockAudioAdapter",
    "SoundDeviceAudioAdapter",
    "SpeechToTextAdapter",
    "MockSpeechToTextAdapter",
    "VoskSpeechToTextAdapter",
    "STTResult",
]
