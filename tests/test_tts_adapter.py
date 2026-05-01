"""Tests for TTS adapters and the get_tts_adapter factory.

All tests run without audio hardware and without piper-tts installed,
relying on mocking/monkeypatching to exercise code paths.
"""
import sys
import types
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cfg(**kwargs):
    """Return a minimal config-like object with the given attributes."""
    cfg = MagicMock()
    cfg.TTS_BACKEND = kwargs.get("TTS_BACKEND", "pyttsx3")
    cfg.PIPER_VOICE_MODEL = kwargs.get("PIPER_VOICE_MODEL", "")
    return cfg


def _make_audio_chunk(sample_rate=22050, num_samples=100):
    """Build a fake AudioChunk-like object matching the piper-tts 1.3+ API."""
    chunk = MagicMock()
    chunk.sample_rate = sample_rate
    chunk.audio_int16_array = np.zeros(num_samples, dtype=np.int16)
    return chunk


# ---------------------------------------------------------------------------
# MockTTSAdapter
# ---------------------------------------------------------------------------

class TestMockTTSAdapter:
    def test_speak_records_text(self):
        from src.adapters.tts_adapter import MockTTSAdapter

        adapter = MockTTSAdapter()
        adapter.speak("hello")
        adapter.speak("world")
        assert adapter.spoken_texts == ["hello", "world"]

    def test_speak_empty_string_is_recorded(self):
        from src.adapters.tts_adapter import MockTTSAdapter

        adapter = MockTTSAdapter()
        adapter.speak("")
        assert adapter.spoken_texts == [""]


# ---------------------------------------------------------------------------
# PiperTTSAdapter -- construction errors
# ---------------------------------------------------------------------------

class TestPiperTTSAdapterErrors:
    def test_empty_model_path_raises_value_error(self):
        from src.adapters.tts_adapter import PiperTTSAdapter

        with pytest.raises(ValueError, match="PIPER_VOICE_MODEL"):
            PiperTTSAdapter(model_path="")

    def test_piper_not_installed_raises_runtime_error(self):
        from src.adapters.tts_adapter import PiperTTSAdapter

        with patch.dict(sys.modules, {"piper": None, "piper.voice": None}):
            with pytest.raises(RuntimeError, match="piper-tts"):
                PiperTTSAdapter(model_path="/fake/model.onnx")

    def test_sounddevice_not_installed_raises_runtime_error(self):
        from src.adapters.tts_adapter import PiperTTSAdapter

        fake_piper_voice = MagicMock()
        fake_piper_voice.load.return_value = MagicMock()
        fake_piper = types.ModuleType("piper")
        fake_piper.voice = fake_piper_voice

        with patch.dict(sys.modules, {
            "piper": fake_piper,
            "piper.voice": fake_piper_voice,
            "sounddevice": None,
        }):
            with pytest.raises(RuntimeError, match="sounddevice"):
                PiperTTSAdapter(model_path="/fake/model.onnx")


# ---------------------------------------------------------------------------
# PiperTTSAdapter -- speak() behaviour (piper-tts >= 1.3 chunk-based API)
# ---------------------------------------------------------------------------

class TestPiperTTSAdapterSpeak:
    def test_speak_empty_is_no_op(self):
        from src.adapters.tts_adapter import PiperTTSAdapter

        voice_mock = MagicMock()
        fake_sd = MagicMock()

        adapter = PiperTTSAdapter.__new__(PiperTTSAdapter)
        adapter._voice = voice_mock

        with patch.dict(sys.modules, {"sounddevice": fake_sd}):
            adapter.speak("")

        voice_mock.synthesize.assert_not_called()
        fake_sd.play.assert_not_called()

    def test_speak_calls_synthesize_and_plays(self):
        from src.adapters.tts_adapter import PiperTTSAdapter

        chunk = _make_audio_chunk(sample_rate=22050, num_samples=200)
        voice_mock = MagicMock()
        voice_mock.synthesize.return_value = [chunk]

        fake_sd = MagicMock()

        adapter = PiperTTSAdapter.__new__(PiperTTSAdapter)
        adapter._voice = voice_mock

        with patch.dict(sys.modules, {"sounddevice": fake_sd}):
            adapter.speak("hello robot")

        voice_mock.synthesize.assert_called_once_with("hello robot")
        fake_sd.play.assert_called_once()
        fake_sd.wait.assert_called_once()
        # Confirm sample_rate is forwarded correctly
        _, call_kwargs = fake_sd.play.call_args
        assert call_kwargs.get("samplerate") == 22050

    def test_speak_concatenates_multiple_chunks(self):
        from src.adapters.tts_adapter import PiperTTSAdapter

        chunks = [
            _make_audio_chunk(sample_rate=22050, num_samples=100),
            _make_audio_chunk(sample_rate=22050, num_samples=150),
        ]
        voice_mock = MagicMock()
        voice_mock.synthesize.return_value = chunks

        fake_sd = MagicMock()
        played_audio = {}

        def capture_play(audio, samplerate):
            played_audio["audio"] = audio
            played_audio["samplerate"] = samplerate

        fake_sd.play.side_effect = capture_play

        adapter = PiperTTSAdapter.__new__(PiperTTSAdapter)
        adapter._voice = voice_mock

        with patch.dict(sys.modules, {"sounddevice": fake_sd}):
            adapter.speak("two chunks")

        # Both chunks concatenated = 250 samples total
        assert played_audio["audio"].shape == (250,)
        assert played_audio["samplerate"] == 22050

    def test_speak_empty_chunks_is_no_op(self):
        """synthesize() returning an empty iterable should not call sd.play."""
        from src.adapters.tts_adapter import PiperTTSAdapter

        voice_mock = MagicMock()
        voice_mock.synthesize.return_value = []
        fake_sd = MagicMock()

        adapter = PiperTTSAdapter.__new__(PiperTTSAdapter)
        adapter._voice = voice_mock

        with patch.dict(sys.modules, {"sounddevice": fake_sd}):
            adapter.speak("anything")

        fake_sd.play.assert_not_called()


# ---------------------------------------------------------------------------
# get_tts_adapter factory
# ---------------------------------------------------------------------------

class TestGetTtsAdapterFactory:
    def test_mock_backend_returns_mock_adapter(self):
        from src.adapters.tts_adapter import MockTTSAdapter, get_tts_adapter

        cfg = _make_cfg(TTS_BACKEND="mock")
        adapter = get_tts_adapter(cfg)
        assert isinstance(adapter, MockTTSAdapter)

    def test_piper_backend_raises_without_model_path(self):
        from src.adapters.tts_adapter import get_tts_adapter

        cfg = _make_cfg(TTS_BACKEND="piper", PIPER_VOICE_MODEL="")
        with pytest.raises(ValueError, match="PIPER_VOICE_MODEL"):
            get_tts_adapter(cfg)

    def test_unknown_backend_falls_back_to_pyttsx3(self):
        from src.adapters.tts_adapter import Pyttsx3TTSAdapter, get_tts_adapter

        cfg = _make_cfg(TTS_BACKEND="invalid-backend")
        fake_pyttsx3 = MagicMock()
        fake_pyttsx3.init.return_value = MagicMock()
        with patch.dict(sys.modules, {"pyttsx3": fake_pyttsx3}):
            adapter = get_tts_adapter(cfg)
        assert isinstance(adapter, Pyttsx3TTSAdapter)

    def test_pyttsx3_backend_returns_pyttsx3_adapter(self):
        from src.adapters.tts_adapter import Pyttsx3TTSAdapter, get_tts_adapter

        cfg = _make_cfg(TTS_BACKEND="pyttsx3")
        fake_pyttsx3 = MagicMock()
        fake_pyttsx3.init.return_value = MagicMock()
        with patch.dict(sys.modules, {"pyttsx3": fake_pyttsx3}):
            adapter = get_tts_adapter(cfg)
        assert isinstance(adapter, Pyttsx3TTSAdapter)


# ---------------------------------------------------------------------------
# RobotConfig -- TTS env vars are picked up
# ---------------------------------------------------------------------------

class TestRobotConfigTtsFields:
    def test_default_tts_backend_is_pyttsx3(self):
        from src.config import RobotConfig

        cfg = RobotConfig()
        assert cfg.TTS_BACKEND == "pyttsx3"
        assert cfg.PIPER_VOICE_MODEL == ""

    def test_from_env_reads_tts_backend(self, monkeypatch):
        from src.config import RobotConfig

        monkeypatch.setenv("TTS_BACKEND", "piper")
        monkeypatch.setenv("PIPER_VOICE_MODEL", "/models/en_US-lessac-medium.onnx")
        cfg = RobotConfig.from_env()
        assert cfg.TTS_BACKEND == "piper"
        assert cfg.PIPER_VOICE_MODEL == "/models/en_US-lessac-medium.onnx"

    def test_from_env_default_when_not_set(self, monkeypatch):
        from src.config import RobotConfig

        monkeypatch.delenv("TTS_BACKEND", raising=False)
        monkeypatch.delenv("PIPER_VOICE_MODEL", raising=False)
        cfg = RobotConfig.from_env()
        assert cfg.TTS_BACKEND == "pyttsx3"
        assert cfg.PIPER_VOICE_MODEL == ""
