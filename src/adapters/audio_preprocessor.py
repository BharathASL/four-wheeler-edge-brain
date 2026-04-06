"""Audio pre-processing pipeline: noise gate, VAD, and AGC.

All stages operate on raw int16 PCM bytes at the sample rate configured
globally (``STT_SAMPLE_RATE_HZ``, default 16 kHz) and depend only on
``numpy``, which is already a declared project dependency.

Pipeline order (when enabled)::

    noise gate → VAD trim → AGC normalisation

``AUDIO_PREPROCESS_ENABLED`` is the master switch (default ``False``), so
existing behaviour is completely preserved until the flag is explicitly set.

Failure policy
--------------
Any unhandled exception inside the pipeline causes ``process()`` to log a
``WARNING`` and return the original raw bytes unchanged (fail-open).  This
ensures the Vosk STT stage always receives *some* audio and degraded-quality
recognition is preferred over a hard failure.

Observability
-------------
Module-level stats counters are updated on every call:

``get_preprocessor_stats()``  — read-only copy of current counters.
``reset_preprocessor_stats()`` — reset all counters to zero (for testing).
"""
from __future__ import annotations

import logging
import math
from typing import Optional

import numpy as np

from src.config import RobotConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level stats counters
# ---------------------------------------------------------------------------
_STATS: dict[str, int] = {
    "calls": 0,
    "gate_rejections": 0,
    "agc_applied": 0,
    "vad_trims": 0,
}


def get_preprocessor_stats() -> dict[str, int]:
    """Return a snapshot (copy) of current preprocessing stats counters."""
    return dict(_STATS)


def reset_preprocessor_stats() -> None:
    """Reset all stats counters to zero."""
    for key in _STATS:
        _STATS[key] = 0


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_INT16_MAX = 32_767
_INT16_MIN = -32_768


# ---------------------------------------------------------------------------
# Private signal-processing helpers
# ---------------------------------------------------------------------------

def _samples_from_bytes(audio_bytes: bytes) -> np.ndarray:
    """Interpret raw bytes as a flat int16 PCM array."""
    return np.frombuffer(audio_bytes, dtype=np.int16)


def _rms_dbfs(samples: np.ndarray) -> float:
    """Compute RMS level in dBFS (full scale = 32767).

    Returns ``-math.inf`` for silent or empty buffers.
    """
    if samples.size == 0:
        return -math.inf
    rms = math.sqrt(float(np.mean(samples.astype(np.float64) ** 2)))
    if rms < 1e-10:
        return -math.inf
    return 20.0 * math.log10(rms / _INT16_MAX)


def _apply_noise_gate(samples: np.ndarray, threshold_dbfs: float) -> bool:
    """Return ``True`` if the overall RMS is below *threshold_dbfs* (gate fires)."""
    level = _rms_dbfs(samples)
    logger.debug("noise_gate: rms=%.1f dBFS threshold=%.1f dBFS", level, threshold_dbfs)
    return level < threshold_dbfs


def _apply_agc(
    samples: np.ndarray,
    target_dbfs: float,
    max_gain_db: float,
) -> np.ndarray:
    """Normalise RMS to *target_dbfs* with an amplification cap of *max_gain_db*.

    Only gain-up is applied (attenuation is never performed).  Output is
    clipped to the int16 range to prevent overflow.
    """
    rms_db = _rms_dbfs(samples)
    if rms_db == -math.inf:
        return samples

    needed_gain_db = target_dbfs - rms_db
    applied_gain_db = max(0.0, min(needed_gain_db, max_gain_db))

    if applied_gain_db < 0.1:
        # Input is already at or above target — nothing meaningful to do.
        return samples

    gain_linear = 10.0 ** (applied_gain_db / 20.0)
    scaled = samples.astype(np.float64) * gain_linear
    clipped = np.clip(scaled, _INT16_MIN, _INT16_MAX)

    logger.debug(
        "agc: gain=%.1f dB applied (input_rms=%.1f dBFS \u2192 target=%.1f dBFS)",
        applied_gain_db,
        rms_db,
        target_dbfs,
    )
    return clipped.astype(np.int16)


def _apply_vad(
    samples: np.ndarray,
    frame_ms: int,
    padding_ms: int,
    threshold_dbfs: float,
    sample_rate_hz: int,
) -> Optional[np.ndarray]:
    """Trim leading and trailing silence using per-frame energy detection.

    Frames whose RMS level is at or above *threshold_dbfs* are classified
    as voiced.  The retained window includes *padding_ms* of context on each
    side of the first and last voiced frame.

    Returns
    -------
    np.ndarray
        Trimmed int16 samples (possibly the full original array if no
        trimming was needed).
    None
        All frames were classified as silence; the call-site should treat
        this as a gate rejection.
    """
    frame_len = int(sample_rate_hz * frame_ms / 1000)
    if frame_len == 0 or samples.size == 0:
        return samples

    n_full_frames = samples.size // frame_len
    voiced: list[bool] = []

    for i in range(n_full_frames):
        frame = samples[i * frame_len : (i + 1) * frame_len]
        voiced.append(_rms_dbfs(frame) >= threshold_dbfs)

    # Remainder samples (fewer than one full frame) form a final short frame.
    remainder = samples[n_full_frames * frame_len :]
    if remainder.size > 0:
        voiced.append(_rms_dbfs(remainder) >= threshold_dbfs)

    voiced_indices = [i for i, v in enumerate(voiced) if v]
    if not voiced_indices:
        logger.info(
            "vad: no voiced frames detected in %d frames — rejecting",
            len(voiced),
        )
        return None

    pad_frames = max(0, padding_ms // frame_ms) if frame_ms > 0 else 0
    first = max(0, voiced_indices[0] - pad_frames)
    last = min(len(voiced) - 1, voiced_indices[-1] + pad_frames)

    start_sample = first * frame_len
    # If *last* covers the remainder frame (index >= n_full_frames), use end of array.
    end_sample = samples.size if last >= n_full_frames else (last + 1) * frame_len

    trimmed = samples[start_sample:end_sample]
    logger.debug(
        "vad: %d/%d frames voiced, trimmed %d\u2192%d samples, padding=%d ms",
        len(voiced_indices),
        len(voiced),
        samples.size,
        trimmed.size,
        padding_ms,
    )
    return trimmed


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------

class AudioPreprocessor:
    """Apply noise gate, VAD, and AGC to raw PCM audio before STT decoding.

    Stages
    ------
    1. **Noise gate** — reject audio whose overall RMS is below threshold.
    2. **VAD trim** — strip leading/trailing silence, keeping voice + padding.
    3. **AGC** — normalise the surviving audio to a target RMS level.

    Each stage is individually toggleable via ``RobotConfig`` flags.  The
    master switch ``AUDIO_PREPROCESS_ENABLED`` must be ``True`` for any
    processing to occur; when ``False``, ``process()`` is a no-op.
    """

    def __init__(self, cfg: RobotConfig) -> None:
        self._cfg = cfg
        logger.debug(
            "audio_preprocessor: enabled=%s (noise_gate=%s agc=%s vad=%s)",
            cfg.AUDIO_PREPROCESS_ENABLED,
            cfg.AUDIO_NOISE_GATE_ENABLED,
            cfg.AUDIO_AGC_ENABLED,
            cfg.AUDIO_VAD_ENABLED,
        )

    def process(self, audio_bytes: bytes) -> Optional[bytes]:
        """Run the preprocessing pipeline on *audio_bytes*.

        Parameters
        ----------
        audio_bytes:
            Raw int16 PCM bytes from the audio adapter.

        Returns
        -------
        bytes
            Processed audio (same int16 PCM format, may be shorter after VAD).
        None
            Audio was gated (silence or all-silence after VAD).  The caller
            should skip the STT stage.
        bytes (unchanged)
            ``AUDIO_PREPROCESS_ENABLED`` is ``False``, or an exception
            occurred in the pipeline.
        """
        _STATS["calls"] += 1

        if not self._cfg.AUDIO_PREPROCESS_ENABLED:
            return audio_bytes

        try:
            return self._run_pipeline(audio_bytes)
        except Exception:
            logger.warning(
                "audio_preprocessor: pipeline error, returning raw audio",
                exc_info=True,
            )
            return audio_bytes

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------

    def _run_pipeline(self, audio_bytes: bytes) -> Optional[bytes]:
        samples = _samples_from_bytes(audio_bytes)

        # Stage 1: overall noise gate
        if self._cfg.AUDIO_NOISE_GATE_ENABLED:
            if _apply_noise_gate(samples, self._cfg.AUDIO_NOISE_GATE_THRESHOLD_DBFS):
                _STATS["gate_rejections"] += 1
                logger.info(
                    "noise_gate: audio rejected (rms=%.1f dBFS below %.1f dBFS threshold)",
                    _rms_dbfs(samples),
                    self._cfg.AUDIO_NOISE_GATE_THRESHOLD_DBFS,
                )
                return None

        # Stage 2: VAD trim
        if self._cfg.AUDIO_VAD_ENABLED:
            trimmed = _apply_vad(
                samples,
                frame_ms=self._cfg.AUDIO_VAD_FRAME_MS,
                padding_ms=self._cfg.AUDIO_VAD_PADDING_MS,
                threshold_dbfs=self._cfg.AUDIO_VAD_ENERGY_THRESHOLD_DBFS,
                sample_rate_hz=self._cfg.STT_SAMPLE_RATE_HZ,
            )
            if trimmed is None:
                _STATS["gate_rejections"] += 1
                return None
            # Only increment counter if actual trimming occurred
            if trimmed.size < samples.size:
                _STATS["vad_trims"] += 1
            samples = trimmed

        # Stage 3: AGC
        if self._cfg.AUDIO_AGC_ENABLED:
            samples_before_agc = samples.copy()
            samples = _apply_agc(
                samples,
                target_dbfs=self._cfg.AUDIO_AGC_TARGET_DBFS,
                max_gain_db=self._cfg.AUDIO_AGC_MAX_GAIN_DB,
            )
            # Only increment counter if actual gain was applied
            if not np.array_equal(samples, samples_before_agc):
                _STATS["agc_applied"] += 1

        return samples.tobytes()


__all__ = [
    "AudioPreprocessor",
    "get_preprocessor_stats",
    "reset_preprocessor_stats",
]
