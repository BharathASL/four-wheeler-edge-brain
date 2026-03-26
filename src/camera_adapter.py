"""Camera adapter: real and mock implementations.

Real implementation should return numpy arrays (frames). Mock returns a placeholder object.
"""
from typing import Any, Tuple


class CameraAdapter:
    def capture_frame(self) -> Any:
        """Capture a single frame and return it (e.g., numpy array)."""
        raise NotImplementedError()


class MockCameraAdapter(CameraAdapter):
    def capture_frame(self) -> Tuple[int, int, str]:
        # Return a simple tuple representing a fake frame: (w, h, tag)
        return (320, 240, "mock_frame")


__all__ = ["CameraAdapter", "MockCameraAdapter"]
