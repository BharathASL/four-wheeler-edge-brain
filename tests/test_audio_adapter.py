from pathlib import Path

import numpy as np
import pytest

from src.adapters import audio_adapter as audio_module
from src.adapters.audio_adapter import STTResult, SoundDeviceAudioAdapter, StreamingVADAudioAdapter, VoskSpeechToTextAdapter


class _FakeRecognizer:
    def __init__(self, model, sample_rate_hz):
        self.model = model
        self.sample_rate_hz = sample_rate_hz

    def SetWords(self, enabled):
        # Mock implementation; no-op for testing
        pass

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
    model_dir.mkdir(exist_ok=True)

    monkeypatch.setattr(audio_module, "_load_vosk_runtime", lambda: _FakeVoskRuntime)
    adapter = VoskSpeechToTextAdapter(model_path=str(model_dir), sample_rate_hz=16_000)

    result = adapter.transcribe(b"fake-pcm")

    assert isinstance(result, STTResult)
    assert result.text == "dock now"


def test_vosk_adapter_retries_then_succeeds(monkeypatch, tmp_path: Path):
    model_dir = tmp_path / "vosk-model"
    model_dir.mkdir(exist_ok=True)
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

    assert isinstance(result, STTResult)
    assert result.text == "dock now"
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


# ---------------------------------------------------------------------------
# StreamingVADAudioAdapter tests
# ---------------------------------------------------------------------------

_SR = 16_000
_CHUNK_MS = 20
_FRAME_SAMPLES = _SR * _CHUNK_MS // 1000  # 320 samples per frame


def _make_frame(value: int = 0) -> bytes:
    return np.full(_FRAME_SAMPLES, value, dtype=np.int16).tobytes()


# _SPEECH_FRAME: amplitude 3000 → RMS ≈ 3000 → ~-20.8 dBFS (well above -38 gate)
# _NOISE_FRAME:  amplitude  100 → RMS ≈  100 → ~-50.3 dBFS (below -38 gate)
# _SILENCE_FRAME: amplitude   0 → -96 dBFS
_SPEECH_FRAME = _make_frame(3000)
_NOISE_FRAME = _make_frame(100)
_SILENCE_FRAME = _make_frame(0)


class _FakeVad:
    def __init__(self, results: list):
        self._iter = iter(results)

    def is_speech(self, data, sample_rate):
        return next(self._iter, False)


class _FakeVadRuntime:
    def __init__(self, results: list):
        self._results = results

    def Vad(self, aggressiveness):
        return _FakeVad(self._results)


class _FakeStream:
    def __init__(self, frames: list):
        self._iter = iter(frames)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, n):
        raw = next(self._iter, bytes(n * 2))
        return np.frombuffer(raw, dtype=np.int16).copy(), False


class _FakeSoundDevice:
    def __init__(self, frames: list):
        self._frames = frames

    def InputStream(self, **kwargs):
        return _FakeStream(self._frames)


def _make_streaming_adapter(vad_results, frames, **kwargs) -> StreamingVADAudioAdapter:
    """Build a StreamingVADAudioAdapter with injected fakes."""
    params = dict(
        sample_rate_hz=_SR,
        chunk_ms=_CHUNK_MS,
        aggressiveness=2,
        silence_padding_ms=_CHUNK_MS * 3,  # 60 ms → padding_frames = 3
        max_duration_s=10.0,
        min_speech_ms=_CHUNK_MS,            # 20 ms → min_speech_frames = 1
    )
    params.update(kwargs)
    return StreamingVADAudioAdapter(
        **params,
        _webrtcvad_runtime=_FakeVadRuntime(vad_results),
        _sounddevice_runtime=_FakeSoundDevice(frames),
    )


class TestStreamingVADAdapterValidation:
    def test_invalid_sample_rate_raises(self):
        with pytest.raises(RuntimeError, match="sample_rate_hz"):
            StreamingVADAudioAdapter(
                sample_rate_hz=44100,
                _webrtcvad_runtime=_FakeVadRuntime([]),
                _sounddevice_runtime=_FakeSoundDevice([]),
            )

    def test_invalid_chunk_ms_raises(self):
        with pytest.raises(RuntimeError, match="chunk_ms"):
            StreamingVADAudioAdapter(
                chunk_ms=25,
                _webrtcvad_runtime=_FakeVadRuntime([]),
                _sounddevice_runtime=_FakeSoundDevice([]),
            )

    def test_aggressiveness_clamped_to_max(self):
        a = _make_streaming_adapter([], [], aggressiveness=99)
        assert a.aggressiveness == 3

    def test_aggressiveness_clamped_to_min(self):
        a = _make_streaming_adapter([], [], aggressiveness=-5)
        assert a.aggressiveness == 0


class TestStreamingVADStateMachine:
    def test_all_silence_returns_empty_bytes(self):
        frames = [_SILENCE_FRAME] * 5
        vad_results = [False] * 5
        result = _make_streaming_adapter(vad_results, frames).record(0)
        assert result == b""

    def test_speech_then_silence_returns_speech_bytes(self):
        # 3 speech + 3 silence (triggers padding_frames=3)
        frames = [_SPEECH_FRAME] * 3 + [_SILENCE_FRAME] * 3
        vad_results = [True] * 3 + [False] * 3
        result = _make_streaming_adapter(vad_results, frames).record(0)
        # All 6 frames are buffered (3 speech + transition frame + 2 padding)
        assert result == b"".join(frames)

    def test_voice_resumes_in_post_speech_extends_speech(self):
        # speech, silence (→POST_SPEECH), speech (→SPEECH again), 3x silence (→break)
        frames = [_SPEECH_FRAME, _SILENCE_FRAME, _SPEECH_FRAME] + [_SILENCE_FRAME] * 3
        vad_results = [True, False, True, False, False, False]
        result = _make_streaming_adapter(vad_results, frames).record(0)
        assert result == b"".join(frames)

    def test_fragment_shorter_than_min_speech_discarded(self):
        # 1 speech frame (20ms) + 3 silence padding = 4 frames buffered (80ms).
        # min_speech_ms=100ms → min_speech_frames=5; 4 < 5 → discard.
        frames = [_SPEECH_FRAME] + [_SILENCE_FRAME] * 3
        vad_results = [True, False, False, False]
        result = _make_streaming_adapter(
            vad_results, frames, min_speech_ms=_CHUNK_MS * 5
        ).record(0)
        assert result == b""

    def test_max_duration_ceiling_stops_recording(self):
        # max_frames = int(40ms / 20ms) = 2; feed 10 speech frames
        frames = [_SPEECH_FRAME] * 10
        vad_results = [True] * 10
        result = _make_streaming_adapter(
            vad_results, frames, max_duration_s=0.04, min_speech_ms=0
        ).record(0)
        # Exactly 2 frames collected (loop exits at total_frames == max_frames)
        assert len(result) == 2 * _FRAME_SAMPLES * 2

    def test_vad_exception_treated_as_silence(self):
        class _ErrorVad:
            def is_speech(self, data, sample_rate):
                raise OSError("device error")

        class _ErrorVadRuntime:
            def Vad(self, agg):
                return _ErrorVad()

        frames = [_SILENCE_FRAME] * 5
        adapter = StreamingVADAudioAdapter(
            sample_rate_hz=_SR,
            chunk_ms=_CHUNK_MS,
            _webrtcvad_runtime=_ErrorVadRuntime(),
            _sounddevice_runtime=_FakeSoundDevice(frames),
        )
        result = adapter.record(0)
        # All frames treated as non-speech → empty result
        assert result == b""

    def test_play_is_noop(self):
        adapter = _make_streaming_adapter([], [])
        assert adapter.play(b"some-audio") is None


class TestStreamingVADSpeechEnergyGate:
    """Tests for the speech_energy_gate_dbfs threshold on SILENCE→SPEECH transition."""

    def test_default_gate_value(self):
        a = _make_streaming_adapter([], [])
        assert a.speech_energy_gate_dbfs == -38.0

    def test_low_energy_frame_classified_as_speech_is_gated(self):
        # _NOISE_FRAME is at ~-50 dBFS (below -38 gate).
        # VAD fake returns True (speech) for all frames, but energy gate blocks them.
        # With all frames gated, state never leaves SILENCE → returns b"".
        frames = [_NOISE_FRAME] * 5
        vad_results = [True] * 5
        result = _make_streaming_adapter(
            vad_results, frames, speech_energy_gate_dbfs=-38.0
        ).record(0)
        assert result == b""

    def test_high_energy_speech_above_gate_is_captured(self):
        # _SPEECH_FRAME is at ~-21 dBFS (above -38 gate).
        frames = [_SPEECH_FRAME] * 3 + [_SILENCE_FRAME] * 3
        vad_results = [True] * 3 + [False] * 3
        result = _make_streaming_adapter(
            vad_results, frames, speech_energy_gate_dbfs=-38.0
        ).record(0)
        assert result != b""

    def test_noise_burst_followed_by_real_speech_captures_speech(self):
        # First 3 frames: noise (VAD=True, energy below gate → gated).
        # Next 3 frames: real speech (VAD=True, energy above gate → triggers SPEECH).
        # Then 3 silence frames → padding expires → returns speech clip.
        frames = [_NOISE_FRAME] * 3 + [_SPEECH_FRAME] * 3 + [_SILENCE_FRAME] * 3
        vad_results = [True] * 3 + [True] * 3 + [False] * 3
        result = _make_streaming_adapter(
            vad_results, frames, speech_energy_gate_dbfs=-38.0, min_speech_ms=0
        ).record(0)
        # Only frames starting from the first SPEECH_FRAME are buffered
        assert result == b"".join([_SPEECH_FRAME] * 3 + [_SILENCE_FRAME] * 3)

    def test_gate_disabled_at_neg96_allows_low_energy_trigger(self):
        # With gate=-96.0, any is_speech=True triggers SILENCE→SPEECH regardless of level.
        frames = [_NOISE_FRAME] * 3 + [_SILENCE_FRAME] * 3
        vad_results = [True] * 3 + [False] * 3
        result = _make_streaming_adapter(
            vad_results, frames, speech_energy_gate_dbfs=-96.0, min_speech_ms=0
        ).record(0)
        assert result != b""
