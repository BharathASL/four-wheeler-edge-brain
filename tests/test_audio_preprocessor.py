"""Unit tests for src/adapters/audio_preprocessor.py.

All tests use synthetic PCM data generated with numpy.  No hardware,
no Vosk, no sounddevice dependencies are required.
"""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np
import pytest

from src.adapters.audio_preprocessor import (
    AudioPreprocessor,
    get_preprocessor_stats,
    reset_preprocessor_stats,
)
from src.config import RobotConfig

# ---------------------------------------------------------------------------
# Helpers for generating test audio
# ---------------------------------------------------------------------------
SAMPLE_RATE = 16_000
INT16_MAX = 32_767


def _sine_bytes(
    duration_s: float = 1.0,
    freq_hz: float = 440.0,
    amplitude: float = 0.9,
) -> bytes:
    """Return mono int16 PCM bytes for a sine wave at *amplitude* (0-1)."""
    n = int(SAMPLE_RATE * duration_s)
    t = np.linspace(0, duration_s, n, endpoint=False)
    samples = (amplitude * INT16_MAX * np.sin(2 * np.pi * freq_hz * t)).astype(np.int16)
    return samples.tobytes()


def _silence_bytes(duration_s: float = 1.0) -> bytes:
    """Return mono int16 PCM bytes of pure silence (all zeros)."""
    n = int(SAMPLE_RATE * duration_s)
    return np.zeros(n, dtype=np.int16).tobytes()


def _amplitude_for_dbfs(dbfs: float) -> float:
    """Return the sine-wave amplitude fraction (0-1) that yields *dbfs* RMS."""
    # For sine: rms = A * INT16_MAX / sqrt(2)
    # rms_dbfs = 20 * log10(A / sqrt(2))  →  A = 10^(dbfs/20) * sqrt(2)
    return 10.0 ** (dbfs / 20.0) * math.sqrt(2.0)


def _sine_at_dbfs(dbfs: float, duration_s: float = 1.0) -> bytes:
    """Return sine bytes calibrated to produce approximately *dbfs* RMS level."""
    amp = min(1.0, _amplitude_for_dbfs(dbfs))
    return _sine_bytes(duration_s=duration_s, amplitude=amp)


def _rms_dbfs_of_bytes(audio_bytes: bytes) -> float:
    samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float64)
    rms = math.sqrt(float(np.mean(samples ** 2)))
    if rms < 1e-10:
        return -math.inf
    return 20.0 * math.log10(rms / INT16_MAX)


def _preprocess_only_cfg(
    *,
    noise_gate: bool = True,
    noise_gate_threshold: float = -45.0,
    agc: bool = True,
    agc_target: float = -20.0,
    agc_max_gain: float = 24.0,
    vad: bool = True,
    vad_threshold: float = -45.0,
    vad_frame_ms: int = 30,
    vad_padding_ms: int = 300,
) -> RobotConfig:
    """Build a RobotConfig with preprocessing enabled and all other fields at defaults."""
    return replace(
        RobotConfig(),
        AUDIO_PREPROCESS_ENABLED=True,
        AUDIO_NOISE_GATE_ENABLED=noise_gate,
        AUDIO_NOISE_GATE_THRESHOLD_DBFS=noise_gate_threshold,
        AUDIO_AGC_ENABLED=agc,
        AUDIO_AGC_TARGET_DBFS=agc_target,
        AUDIO_AGC_MAX_GAIN_DB=agc_max_gain,
        AUDIO_VAD_ENABLED=vad,
        AUDIO_VAD_ENERGY_THRESHOLD_DBFS=vad_threshold,
        AUDIO_VAD_FRAME_MS=vad_frame_ms,
        AUDIO_VAD_PADDING_MS=vad_padding_ms,
        STT_SAMPLE_RATE_HZ=SAMPLE_RATE,
    )


@pytest.fixture(autouse=True)
def _reset_stats():
    """Reset stats counters before and after every test."""
    reset_preprocessor_stats()
    yield
    reset_preprocessor_stats()


# ---------------------------------------------------------------------------
# Master toggle
# ---------------------------------------------------------------------------

class TestMasterToggle:
    def test_disabled_returns_raw_audio_unchanged(self):
        cfg = RobotConfig()  # AUDIO_PREPROCESS_ENABLED defaults to False
        assert not cfg.AUDIO_PREPROCESS_ENABLED
        p = AudioPreprocessor(cfg)
        audio = _sine_bytes()
        assert p.process(audio) is audio  # identical object (no copy made)

    def test_disabled_does_not_update_calls_counter(self):
        p = AudioPreprocessor(RobotConfig())
        p.process(_silence_bytes())
        # calls counter is still incremented even in disabled path
        assert get_preprocessor_stats()["calls"] == 1

    def test_disabled_returns_silence_as_is(self):
        p = AudioPreprocessor(RobotConfig())
        silence = _silence_bytes()
        result = p.process(silence)
        assert result == silence


# ---------------------------------------------------------------------------
# Noise gate
# ---------------------------------------------------------------------------

class TestNoiseGate:
    def test_silence_is_gated(self):
        cfg = _preprocess_only_cfg(agc=False, vad=False)
        p = AudioPreprocessor(cfg)
        assert p.process(_silence_bytes()) is None

    def test_loud_audio_passes_gate(self):
        cfg = _preprocess_only_cfg(agc=False, vad=False)
        p = AudioPreprocessor(cfg)
        result = p.process(_sine_bytes(amplitude=0.9))
        assert result is not None
        assert len(result) > 0

    def test_gate_rejection_increments_counter(self):
        cfg = _preprocess_only_cfg(agc=False, vad=False)
        p = AudioPreprocessor(cfg)
        p.process(_silence_bytes())
        assert get_preprocessor_stats()["gate_rejections"] == 1

    def test_gate_disabled_passes_silence(self):
        cfg = _preprocess_only_cfg(noise_gate=False, agc=False, vad=False)
        p = AudioPreprocessor(cfg)
        result = p.process(_silence_bytes())
        assert result is not None  # silence passes through when gate disabled

    def test_gate_threshold_boundary_below(self):
        # Audio just below threshold must be gated.
        threshold = -30.0
        cfg = _preprocess_only_cfg(noise_gate_threshold=threshold, agc=False, vad=False)
        p = AudioPreprocessor(cfg)
        audio = _sine_at_dbfs(-35.0)  # 5 dB below threshold
        assert p.process(audio) is None

    def test_gate_threshold_boundary_above(self):
        # Audio above threshold must pass.
        threshold = -30.0
        cfg = _preprocess_only_cfg(noise_gate_threshold=threshold, agc=False, vad=False)
        p = AudioPreprocessor(cfg)
        audio = _sine_at_dbfs(-25.0)  # 5 dB above threshold
        assert p.process(audio) is not None


# ---------------------------------------------------------------------------
# AGC
# ---------------------------------------------------------------------------

class TestAGC:
    def test_agc_normalises_quiet_audio_to_near_target(self):
        target_dbfs = -20.0
        # Input at ~-35 dBFS (well above gate threshold of -45 dBFS).
        cfg = _preprocess_only_cfg(
            noise_gate_threshold=-45.0,
            agc_target=target_dbfs,
            agc_max_gain=24.0,
            vad=False,
        )
        p = AudioPreprocessor(cfg)
        audio = _sine_at_dbfs(-35.0)
        result = p.process(audio)
        assert result is not None
        out_dbfs = _rms_dbfs_of_bytes(result)
        # Expect output within 1.5 dB of target
        assert abs(out_dbfs - target_dbfs) < 1.5, f"output={out_dbfs:.1f} dBFS, target={target_dbfs}"

    def test_agc_respects_max_gain_cap(self):
        # With gate off and a very tight max_gain_db=6, quiet audio should
        # reach only input_rms + 6 dB, not the full target.
        input_dbfs = -35.0
        max_gain = 6.0
        expected_max_output = input_dbfs + max_gain  # -29 dBFS
        cfg = _preprocess_only_cfg(
            noise_gate=False,
            agc_target=-20.0,
            agc_max_gain=max_gain,
            vad=False,
        )
        p = AudioPreprocessor(cfg)
        audio = _sine_at_dbfs(input_dbfs)
        result = p.process(audio)
        out_dbfs = _rms_dbfs_of_bytes(result)
        # Must NOT reach target; must be at most input + max_gain (+ tolerance)
        assert out_dbfs < -20.0 + 1.0, f"output={out_dbfs:.1f} exceeded target -20 dBFS"
        assert out_dbfs <= expected_max_output + 1.5, (
            f"output={out_dbfs:.1f} exceeded max-gain ceiling {expected_max_output:.1f} dBFS"
        )

    def test_agc_output_is_valid_int16_range(self):
        cfg = _preprocess_only_cfg(noise_gate=False, vad=False, agc_max_gain=40.0)
        p = AudioPreprocessor(cfg)
        audio = _sine_at_dbfs(-35.0)
        result = p.process(audio)
        assert result is not None
        samples = np.frombuffer(result, dtype=np.int16)
        assert samples.min() >= -32768
        assert samples.max() <= 32767

    def test_agc_disabled_leaves_amplitude_unchanged(self):
        cfg = _preprocess_only_cfg(noise_gate=False, agc=False, vad=False)
        p = AudioPreprocessor(cfg)
        audio = _sine_at_dbfs(-35.0)
        result = p.process(audio)
        assert result is not None
        in_dbfs = _rms_dbfs_of_bytes(audio)
        out_dbfs = _rms_dbfs_of_bytes(result)
        assert abs(out_dbfs - in_dbfs) < 0.1, "AGC disabled but amplitude changed"

    def test_agc_applied_counter_increments(self):
        cfg = _preprocess_only_cfg(noise_gate=False, agc=True, vad=False)
        p = AudioPreprocessor(cfg)
        p.process(_sine_at_dbfs(-35.0))
        assert get_preprocessor_stats()["agc_applied"] == 1

    def test_agc_does_not_attenuate_loud_audio(self):
        # Loud input already at target level — AGC should change nothing.
        target_dbfs = -20.0
        cfg = _preprocess_only_cfg(noise_gate=False, agc=True, agc_target=target_dbfs, vad=False)
        p = AudioPreprocessor(cfg)
        audio = _sine_at_dbfs(target_dbfs)
        result = p.process(audio)
        in_dbfs = _rms_dbfs_of_bytes(audio)
        out_dbfs = _rms_dbfs_of_bytes(result)
        # Output should not be quieter than input (no attenuation)
        assert out_dbfs >= in_dbfs - 0.5


# ---------------------------------------------------------------------------
# VAD
# ---------------------------------------------------------------------------

class TestVAD:
    def _voice_in_silence(
        self,
        silence_before_s: float = 1.0,
        voice_s: float = 0.3,
        silence_after_s: float = 1.0,
    ) -> bytes:
        """Build: [silence][voice][silence] PCM bytes."""
        silence1 = np.zeros(int(SAMPLE_RATE * silence_before_s), dtype=np.int16)
        t = np.linspace(0, voice_s, int(SAMPLE_RATE * voice_s), endpoint=False)
        voice = (0.9 * INT16_MAX * np.sin(2 * np.pi * 440 * t)).astype(np.int16)
        silence2 = np.zeros(int(SAMPLE_RATE * silence_after_s), dtype=np.int16)
        return np.concatenate([silence1, voice, silence2]).tobytes()

    def test_vad_trims_leading_silence(self):
        cfg = _preprocess_only_cfg(noise_gate=False, agc=False, vad_padding_ms=0)
        p = AudioPreprocessor(cfg)
        audio = self._voice_in_silence(silence_before_s=1.0, voice_s=0.3, silence_after_s=0.0)
        result = p.process(audio)
        assert result is not None
        # Output must be shorter than input
        assert len(result) < len(audio)

    def test_vad_trims_trailing_silence(self):
        cfg = _preprocess_only_cfg(noise_gate=False, agc=False, vad_padding_ms=0)
        p = AudioPreprocessor(cfg)
        audio = self._voice_in_silence(silence_before_s=0.0, voice_s=0.3, silence_after_s=1.0)
        result = p.process(audio)
        assert result is not None
        assert len(result) < len(audio)

    def test_vad_trims_both_sides(self):
        cfg = _preprocess_only_cfg(noise_gate=False, agc=False, vad_padding_ms=0)
        p = AudioPreprocessor(cfg)
        audio = self._voice_in_silence(silence_before_s=1.0, voice_s=0.3, silence_after_s=1.0)
        result = p.process(audio)
        assert result is not None
        # 2.3 s total → output should be significantly shorter
        assert len(result) < len(audio) * 0.6

    def test_vad_preserves_padding(self):
        padding_ms = 300
        cfg = _preprocess_only_cfg(
            noise_gate=False,
            agc=False,
            vad_padding_ms=padding_ms,
            vad_frame_ms=30,
        )
        p = AudioPreprocessor(cfg)
        # 1s silence + 0.3s voice + 1s silence = 2.3 s total
        audio = self._voice_in_silence(silence_before_s=1.0, voice_s=0.3, silence_after_s=1.0)
        no_pad_cfg = _preprocess_only_cfg(noise_gate=False, agc=False, vad_padding_ms=0)
        result_no_pad = AudioPreprocessor(no_pad_cfg).process(audio)
        result_with_pad = p.process(audio)
        assert result_with_pad is not None
        assert result_no_pad is not None
        # With padding, output must be longer than without padding
        assert len(result_with_pad) > len(result_no_pad)

    def test_vad_rejects_all_silence(self):
        cfg = _preprocess_only_cfg(noise_gate=False, agc=False)
        p = AudioPreprocessor(cfg)
        assert p.process(_silence_bytes(duration_s=2.0)) is None

    def test_vad_keeps_full_voice_audio(self):
        cfg = _preprocess_only_cfg(noise_gate=False, agc=False, vad_padding_ms=0)
        p = AudioPreprocessor(cfg)
        audio = _sine_bytes(duration_s=1.0, amplitude=0.9)  # all voiced
        result = p.process(audio)
        # Output should be the full audio (all frames voiced)
        assert result is not None
        assert len(result) == len(audio)

    def test_vad_disabled_returns_untrimmed_audio(self):
        cfg = _preprocess_only_cfg(noise_gate=False, agc=False, vad=False)
        p = AudioPreprocessor(cfg)
        audio = self._voice_in_silence(silence_before_s=1.0, voice_s=0.3, silence_after_s=1.0)
        result = p.process(audio)
        assert result is not None
        assert len(result) == len(audio)  # no trimming without VAD

    def test_vad_trim_increments_counter(self):
        cfg = _preprocess_only_cfg(noise_gate=False, agc=False)
        p = AudioPreprocessor(cfg)
        audio = self._voice_in_silence()
        p.process(audio)
        assert get_preprocessor_stats()["vad_trims"] == 1

    def test_vad_rejection_not_counted_as_trim(self):
        cfg = _preprocess_only_cfg(noise_gate=False, agc=False)
        p = AudioPreprocessor(cfg)
        p.process(_silence_bytes())
        stats = get_preprocessor_stats()
        assert stats["vad_trims"] == 0
        assert stats["gate_rejections"] == 1

    def test_vad_runs_before_agc(self):
        """AGC operates on the VAD-trimmed (shorter) audio, not the original full buffer."""
        cfg = _preprocess_only_cfg(noise_gate=False, agc=True, vad=True, vad_padding_ms=0)
        p = AudioPreprocessor(cfg)
        audio = self._voice_in_silence(silence_before_s=0.8, voice_s=0.4, silence_after_s=0.8)
        result = p.process(audio)
        assert result is not None
        # The output is shorter than the input because VAD trimmed before AGC.
        assert len(result) < len(audio)


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_silence_returns_none(self):
        cfg = _preprocess_only_cfg()
        p = AudioPreprocessor(cfg)
        assert p.process(_silence_bytes(duration_s=3.0)) is None

    def test_voice_returns_processed_bytes(self):
        cfg = _preprocess_only_cfg()
        p = AudioPreprocessor(cfg)
        result = p.process(_sine_bytes(duration_s=1.0, amplitude=0.9))
        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0
        # Must be decodable as int16
        samples = np.frombuffer(result, dtype=np.int16)
        assert samples.dtype == np.int16


# ---------------------------------------------------------------------------
# Exception fallback
# ---------------------------------------------------------------------------

class TestFallback:
    def test_corrupted_bytes_returns_raw_audio(self):
        """Odd-length bytes cannot be decoded as int16; pipeline must not raise."""
        cfg = _preprocess_only_cfg()
        p = AudioPreprocessor(cfg)
        bad_audio = b"\x01\x02\x03"  # odd-length — numpy frombuffer raises ValueError
        result = p.process(bad_audio)
        # Must return the original bytes, not raise
        assert result == bad_audio

    def test_empty_bytes_passes_through_when_disabled(self):
        p = AudioPreprocessor(RobotConfig())
        assert p.process(b"") == b""

    def test_fallback_does_not_corrupt_stats_calls_counter(self):
        cfg = _preprocess_only_cfg()
        p = AudioPreprocessor(cfg)
        p.process(b"\x01\x02\x03")
        assert get_preprocessor_stats()["calls"] == 1


# ---------------------------------------------------------------------------
# Stats counters
# ---------------------------------------------------------------------------

class TestStats:
    def test_calls_counter_increments_each_call(self):
        p = AudioPreprocessor(RobotConfig())
        for i in range(3):
            p.process(_silence_bytes())
        assert get_preprocessor_stats()["calls"] == 3

    def test_reset_clears_all_counters(self):
        cfg = _preprocess_only_cfg(agc=False, vad=False)
        p = AudioPreprocessor(cfg)
        p.process(_silence_bytes())  # gate rejection
        assert get_preprocessor_stats()["gate_rejections"] == 1
        reset_preprocessor_stats()
        stats = get_preprocessor_stats()
        assert all(v == 0 for v in stats.values())

    def test_get_stats_returns_copy(self):
        stats = get_preprocessor_stats()
        stats["calls"] = 9999
        assert get_preprocessor_stats()["calls"] != 9999
