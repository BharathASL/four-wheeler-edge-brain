from pathlib import Path

import pytest

from src.adapters import audio_adapter as audio_module
from src.adapters.audio_adapter import SoundDeviceAudioAdapter, VoskSpeechToTextAdapter


class _FakeRecognizer:
    def __init__(self, model, sample_rate_hz):
        self.model = model
        self.sample_rate_hz = sample_rate_hz

    def AcceptWaveform(self, audio_data):
        return False

    def Result(self):
        return '{"text": "ignored"}'

    def FinalResult(self):
        return '{"text": "dock now"}'


class _FakeVoskRuntime:
    class Model:
        def __init__(self, path):
            self.path = path

    KaldiRecognizer = _FakeRecognizer


def test_vosk_adapter_requires_model_path():
    with pytest.raises(RuntimeError, match="model path"):
        VoskSpeechToTextAdapter(model_path="")


def test_vosk_adapter_requires_existing_model_path(tmp_path: Path):
    missing_path = tmp_path / "missing-model-dir"
    with pytest.raises(RuntimeError, match="does not exist"):
        VoskSpeechToTextAdapter(model_path=str(missing_path))


def test_vosk_adapter_transcribes_final_text(monkeypatch, tmp_path: Path):
    model_dir = tmp_path / "vosk-model"
    model_dir.mkdir()

    monkeypatch.setattr(audio_module, "_load_vosk_runtime", lambda: _FakeVoskRuntime)
    adapter = VoskSpeechToTextAdapter(model_path=str(model_dir), sample_rate_hz=16_000)

    result = adapter.transcribe(b"fake-pcm")

    assert result == "dock now"


def test_vosk_adapter_retries_then_succeeds(monkeypatch, tmp_path: Path):
    model_dir = tmp_path / "vosk-model"
    model_dir.mkdir()
    attempts = {"count": 0}

    class _RetryRecognizer(_FakeRecognizer):
        def AcceptWaveform(self, audio_data):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise RuntimeError("temporary failure")
            return False

    class _RetryRuntime:
        class Model:
            def __init__(self, path):
                self.path = path

        KaldiRecognizer = _RetryRecognizer

    monkeypatch.setattr(audio_module, "_load_vosk_runtime", lambda: _RetryRuntime)
    monkeypatch.setattr(audio_module.time, "sleep", lambda _: None)

    adapter = VoskSpeechToTextAdapter(
        model_path=str(model_dir),
        max_retries=2,
        retry_backoff_s=0.01,
    )

    result = adapter.transcribe(b"fake-pcm")

    assert result == "dock now"
    assert attempts["count"] == 2


def test_vosk_adapter_exhausts_retries(monkeypatch, tmp_path: Path):
    model_dir = tmp_path / "vosk-model"
    model_dir.mkdir()

    class _FailRecognizer(_FakeRecognizer):
        def AcceptWaveform(self, audio_data):
            raise RuntimeError("always fails")

    class _FailRuntime:
        class Model:
            def __init__(self, path):
                self.path = path

        KaldiRecognizer = _FailRecognizer

    monkeypatch.setattr(audio_module, "_load_vosk_runtime", lambda: _FailRuntime)
    monkeypatch.setattr(audio_module.time, "sleep", lambda _: None)

    adapter = VoskSpeechToTextAdapter(
        model_path=str(model_dir),
        max_retries=1,
        retry_backoff_s=0.01,
    )

    with pytest.raises(RuntimeError, match="transcription failed"):
        adapter.transcribe(b"fake-pcm")


def test_sounddevice_audio_adapter_records_pcm(monkeypatch):
    class _FakeRecording:
        def tobytes(self):
            return b"pcm-data"

    class _FakeSoundDevice:
        def rec(self, frames, samplerate, channels, dtype):
            assert frames > 0
            assert samplerate == 16_000
            assert channels == 1
            assert dtype == "int16"
            return _FakeRecording()

        def wait(self):
            return None

    monkeypatch.setattr(audio_module, "_load_sounddevice_runtime", lambda: _FakeSoundDevice())

    adapter = SoundDeviceAudioAdapter(sample_rate_hz=16_000, channels=1)
    captured = adapter.record(0.1)

    assert captured == b"pcm-data"


def test_sounddevice_audio_adapter_maps_record_errors(monkeypatch):
    class _FailSoundDevice:
        def rec(self, frames, samplerate, channels, dtype):
            raise RuntimeError("input device missing")

        def wait(self):
            return None

    monkeypatch.setattr(audio_module, "_load_sounddevice_runtime", lambda: _FailSoundDevice())

    adapter = SoundDeviceAudioAdapter(sample_rate_hz=16_000, channels=1)
    with pytest.raises(RuntimeError, match="audio capture failed"):
        adapter.record(0.2)
