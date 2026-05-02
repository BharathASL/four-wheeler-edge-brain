"""TTS adapter: real and mock implementations.

Keeps speech output behind a small interface so simulation, tests, and future
hardware integrations can swap backends safely.

Backends
--------
pyttsx3  -- legacy espeak-ng wrapper; dev-only, rough quality.
piper    -- Piper TTS (offline, neural, Pi-compatible). Requires a .onnx voice
            model file; see docs/phase1/PIPER_SETUP.md for download instructions.
            Uses piper-tts >= 1.3.0 (OHF-Voice/piper1-gpl); synthesize() returns
            AudioChunk objects rather than writing to a WAV file.
mock     -- silent stub for unit tests and headless environments.

Use ``get_tts_adapter(cfg)`` to construct the right backend from a
``RobotConfig`` instance rather than instantiating adapters directly.
"""
from __future__ import annotations

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


class PiperTTSAdapter(TTSAdapter):
    """Piper TTS adapter -- offline, neural, Raspberry Pi compatible.

    Piper produces high-quality speech from an ONNX voice model entirely
    on-device (no network, no cloud). It runs in WSL today via PulseAudio
    and targets the Pi 4 in production.

    Requires piper-tts >= 1.3.0 (OHF-Voice/piper1-gpl). The synthesize()
    method returns an iterable of AudioChunk objects; each chunk exposes
    ``audio_int16_array`` (numpy int16) and ``sample_rate`` directly so no
    intermediate WAV file is needed.

    Parameters
    ----------
    model_path:
        Absolute or relative path to a Piper ``.onnx`` voice model file.
        Download voices from https://github.com/rhasspy/piper/releases or
        https://github.com/OHF-Voice/piper1-gpl/releases
        (e.g. ``en_US-lessac-medium.onnx``).

    Raises
    ------
    ValueError
        If *model_path* is empty.
    RuntimeError
        If ``piper-tts`` or ``sounddevice`` is not installed.
    """

    def __init__(self, model_path: str) -> None:
        if not model_path:
            raise ValueError(
                "PIPER_VOICE_MODEL must point to a .onnx model file. "
                "Download one from https://github.com/OHF-Voice/piper1-gpl/releases "
                "and set PIPER_VOICE_MODEL=/path/to/en_US-lessac-medium.onnx"
            )
        try:
            from piper.voice import PiperVoice  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "piper-tts is not available -- run: pip install piper-tts"
            ) from exc
        try:
            import sounddevice  # type: ignore  # noqa: F401
        except Exception as exc:
            raise RuntimeError(
                "sounddevice is not available -- run: pip install sounddevice"
            ) from exc

        self._voice = PiperVoice.load(model_path)

    def speak(self, text: str) -> None:
        """Synthesize *text* and play it through the default audio device.

        All AudioChunks are accumulated before playback so there are no
        audible gaps between sentence segments.
        """
        if not text:
            return

        import numpy as np  # type: ignore
        import sounddevice as sd  # type: ignore

        # synthesize() returns Iterable[AudioChunk]; each chunk carries
        # audio_int16_array (np.int16) and sample_rate.
        chunks = list(self._voice.synthesize(text))
        if not chunks:
            return

        audio = np.concatenate([chunk.audio_int16_array for chunk in chunks])
        sample_rate = chunks[0].sample_rate

        sd.play(audio, samplerate=sample_rate)
        sd.wait()


class MockTTSAdapter(TTSAdapter):
    """Mock adapter for unit tests and no-audio environments."""

    def __init__(self):
        self.spoken_texts: list = []

    def speak(self, text: str) -> None:
        self.spoken_texts.append(text)


def get_tts_adapter(cfg) -> TTSAdapter:
    """Factory: construct the right TTS adapter from *cfg* (a ``RobotConfig``).

    Reads ``cfg.TTS_BACKEND`` to dispatch:

    * ``"piper"``   -> :class:`PiperTTSAdapter` using ``cfg.PIPER_VOICE_MODEL``
    * ``"mock"``    -> :class:`MockTTSAdapter`
    * anything else -> :class:`Pyttsx3TTSAdapter` (default / legacy)
    """
    backend = (getattr(cfg, "TTS_BACKEND", "pyttsx3") or "pyttsx3").strip().lower()
    if backend == "piper":
        return PiperTTSAdapter(model_path=getattr(cfg, "PIPER_VOICE_MODEL", ""))
    if backend == "mock":
        return MockTTSAdapter()
    return Pyttsx3TTSAdapter()


__all__ = [
    "TTSAdapter",
    "Pyttsx3TTSAdapter",
    "PiperTTSAdapter",
    "MockTTSAdapter",
    "get_tts_adapter",
]
