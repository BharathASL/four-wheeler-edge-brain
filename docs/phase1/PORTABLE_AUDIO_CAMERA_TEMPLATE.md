# Portable Audio + Camera Template (WSLg + Raspberry Pi)

This template provides one interface pattern and two runtime backends so the same Phase-1 code runs in development (WSLg) and production (Raspberry Pi).

## 1) Keep one adapter interface

Use the existing contracts in src/audio_adapter.py and src/camera_adapter.py:

- AudioAdapter.record(duration: float) -> bytes
- AudioAdapter.play(audio_data: bytes) -> None
- CameraAdapter.capture_frame() -> frame

## 2) Select backend by platform

Recommended detection pattern:

```python
import platform

IS_WINDOWS = platform.system() == "Windows"
IS_PI = platform.machine().startswith("arm") or "raspberry" in platform.uname().node.lower()
```

Backend policy:

- Dev (Windows/WSL): allow mock adapters by default.
- Pi (arm/aarch64): require real camera/audio adapters.
- Unknown platform: fall back to mock with warning log.

## 3) Environment variables

- ROBOT_ENV=dev|prod
- AUDIO_BACKEND=mock|sounddevice
- CAMERA_BACKEND=mock|opencv

Example:

```bash
export ROBOT_ENV=dev
export AUDIO_BACKEND=mock
export CAMERA_BACKEND=mock
```

## 4) WSLg checklist (development)

- Attach USB camera to WSL if needed (usbipd on Windows).
- Verify /dev/video0 exists in WSL.
- Prefer mock audio in tests for deterministic CI behavior.
- Use real camera only in manual local runs.

## 5) Pi checklist (production)

- Install system dependencies for OpenCV and audio stack.
- Verify camera availability with v4l2 tools.
- Verify playback/capture devices before robot start.
- Keep a mock fallback mode for diagnostics.

## 6) Minimal factory template

```python
import os

from src.audio_adapter import MockAudioAdapter
from src.camera_adapter import MockCameraAdapter


def build_audio_adapter():
    backend = os.getenv("AUDIO_BACKEND", "mock")
    if backend == "mock":
        return MockAudioAdapter()
    # Replace with real adapter class when audio stack is integrated.
    return MockAudioAdapter()


def build_camera_adapter():
    backend = os.getenv("CAMERA_BACKEND", "mock")
    if backend == "mock":
        return MockCameraAdapter()
    # Replace with real adapter class when camera stack is integrated.
    return MockCameraAdapter()
```

## 7) Validation matrix

- Dev quick test: mock audio + mock camera
- Dev manual test: mock audio + real camera
- Pi smoke test: real audio + real camera
- CI test: mock audio + mock camera

## 8) Failure policy

- If real backend init fails, log the reason.
- In dev, fallback to mock.
- In prod, return clear startup error and exit non-zero unless explicitly configured to fallback.
