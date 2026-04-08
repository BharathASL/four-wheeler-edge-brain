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


def _load_webrtcvad_runtime() -> Any:
    """Load and return the webrtcvad runtime module lazily."""
    try:
        return import_module("webrtcvad")
    except Exception as exc:
        raise RuntimeError(
            "webrtcvad runtime is unavailable; install with: pip install webrtcvad-wheels"
        ) from exc


def _rms_dbfs_frame(frame_bytes: bytes) -> float:
    """Return RMS level in dBFS for a raw int16 PCM byte string.

    Returns -96.0 for empty or zero-signal frames.
    """
    import math
    import struct
    n = len(frame_bytes) // 2
    if n == 0:
        return -96.0
    samples = struct.unpack(f"{n}h", frame_bytes)
    rms = math.sqrt(sum(s * s for s in samples) / n)
    return 20.0 * math.log10(max(rms, 1.0) / 32768.0)


class _VadState:
    SILENCE = "SILENCE"
    SPEECH = "SPEECH"
    POST_SPEECH = "POST_SPEECH"


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


class StreamingVADAudioAdapter(AudioAdapter):
    """Streaming audio recorder using webrtcvad for capture-time voice detection.

    Unlike ``SoundDeviceAudioAdapter`` (fixed-duration), this adapter streams
    audio in small chunks and returns only frames that contain speech,
    eliminating silence and background noise before Vosk decoding.

    VAD state machine::

        SILENCE  --(voice detected)--> SPEECH
        SPEECH   --(silence detected)-> POST_SPEECH
        POST_SPEECH --(padding expires)--> return buffer
        POST_SPEECH --(voice resumes)---> SPEECH

    Returns ``b""`` when the captured speech is shorter than
    ``min_speech_ms`` so the caller treats the window as a non-event.

    Supported sample rates: 8000, 16000, 32000, 48000 Hz.
    Supported chunk sizes: 10, 20, or 30 ms (webrtcvad constraint).
    """

    _VALID_SAMPLE_RATES = (8000, 16000, 32000, 48000)
    _VALID_CHUNK_MS = (10, 20, 30)

    def __init__(
        self,
        sample_rate_hz: int = 16_000,
        aggressiveness: int = 2,
        chunk_ms: int = 20,
        silence_padding_ms: int = 400,
        max_duration_s: float = 8.0,
        min_speech_ms: int = 100,
        speech_energy_gate_dbfs: float = -38.0,
        _webrtcvad_runtime=None,
        _sounddevice_runtime=None,
    ):
        if sample_rate_hz not in self._VALID_SAMPLE_RATES:
            raise RuntimeError(
                f"sample_rate_hz {sample_rate_hz} not supported by webrtcvad; "
                f"must be one of {self._VALID_SAMPLE_RATES}"
            )
        if chunk_ms not in self._VALID_CHUNK_MS:
            raise RuntimeError(
                f"chunk_ms {chunk_ms} not supported by webrtcvad; "
                f"must be one of {self._VALID_CHUNK_MS}"
            )
        self.sample_rate_hz = sample_rate_hz
        self.aggressiveness = max(0, min(3, int(aggressiveness)))
        self.chunk_ms = chunk_ms
        self.silence_padding_ms = max(0, int(silence_padding_ms))
        self.max_duration_s = max(0.5, float(max_duration_s))
        self.min_speech_ms = max(0, int(min_speech_ms))
        self.speech_energy_gate_dbfs = float(speech_energy_gate_dbfs)

        self._frame_samples = (sample_rate_hz * chunk_ms) // 1000
        self._padding_frames = max(
            1, (silence_padding_ms + chunk_ms - 1) // chunk_ms
        )
        self._max_frames = int(max_duration_s * 1000 / chunk_ms)
        self._min_speech_frames = max(
            1, (min_speech_ms + chunk_ms - 1) // chunk_ms
        )

        self._vad_runtime = _webrtcvad_runtime or _load_webrtcvad_runtime()
        self._sd_runtime = _sounddevice_runtime or _load_sounddevice_runtime()

    def record(self, duration: float) -> bytes:  # noqa: ARG002
        """Stream and return one speech utterance as int16 PCM bytes.

        The *duration* parameter is accepted for interface compatibility and
        ignored; recording stops when VAD detects end of speech or
        ``max_duration_s`` is reached.
        Returns ``b""`` when no usable speech was detected.
        """
        vad = self._vad_runtime.Vad(self.aggressiveness)
        state = _VadState.SILENCE
        speech_frames: list[bytes] = []
        silence_count = 0
        total_frames = 0

        with self._sd_runtime.InputStream(
            samplerate=self.sample_rate_hz,
            channels=1,
            dtype="int16",
            blocksize=self._frame_samples,
        ) as stream:
            while total_frames < self._max_frames:
                frame_data, _ = stream.read(self._frame_samples)
                frame_bytes = frame_data.tobytes()
                total_frames += 1

                is_speech = False
                try:
                    is_speech = vad.is_speech(frame_bytes, self.sample_rate_hz)
                except Exception:
                    logger.warning("webrtcvad_frame_error frame_idx=%d", total_frames)

                if state == _VadState.SILENCE:
                    if is_speech and _rms_dbfs_frame(frame_bytes) >= self.speech_energy_gate_dbfs:
                        state = _VadState.SPEECH
                        speech_frames.append(frame_bytes)
                        logger.debug("vad_stream_voice_start frame=%d", total_frames)
                    elif is_speech:
                        logger.debug(
                            "vad_stream_noise_gate filtered dbfs=%.1f gate=%.1f frame=%d",
                            _rms_dbfs_frame(frame_bytes),
                            self.speech_energy_gate_dbfs,
                            total_frames,
                        )

                elif state == _VadState.SPEECH:
                    speech_frames.append(frame_bytes)
                    if not is_speech:
                        state = _VadState.POST_SPEECH
                        silence_count = 1

                elif state == _VadState.POST_SPEECH:
                    speech_frames.append(frame_bytes)
                    if is_speech:
                        state = _VadState.SPEECH
                        silence_count = 0
                    else:
                        silence_count += 1
                        if silence_count >= self._padding_frames:
                            logger.debug(
                                "vad_stream_speech_end frames=%d total_frames=%d",
                                len(speech_frames),
                                total_frames,
                            )
                            break

        if len(speech_frames) < self._min_speech_frames:
            logger.debug(
                "vad_stream_fragment_discarded frames=%d min_frames=%d",
                len(speech_frames),
                self._min_speech_frames,
            )
            return b""

        result = b"".join(speech_frames)
        logger.debug("vad_stream_captured bytes=%d", len(result))
        return result

    def play(self, audio_data: bytes) -> None:
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
        recognizer.SetWords(True)

        # Feed audio in 4000-sample chunks so Vosk can track intermediate state,
        # then always call FinalResult() to flush the full decoded buffer.
        chunk_bytes = 4000 * 2  # 4000 int16 samples
        offset = 0
        while offset < len(audio_data):
            recognizer.AcceptWaveform(audio_data[offset : offset + chunk_bytes])
            offset += chunk_bytes

        payload = recognizer.FinalResult()

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
    "StreamingVADAudioAdapter",
    "SpeechToTextAdapter",
    "MockSpeechToTextAdapter",
    "VoskSpeechToTextAdapter",
    "STTResult",
]
