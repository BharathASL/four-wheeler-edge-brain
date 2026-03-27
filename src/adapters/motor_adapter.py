"""Motor adapter: future real backend plus deterministic mock for tests.

The contract is intentionally small so the command/executor layer can stay
independent from any eventual GPIO, PWM, or motor-HAT implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class MotorCommand:
    linear_mps: float
    angular_dps: float


class MotorAdapter:
    def set_motion(self, linear_mps: float, angular_dps: float) -> None:
        """Apply a linear/angular velocity command to the drive base."""
        raise NotImplementedError()

    def stop(self) -> None:
        """Bring the drive base to a stop."""
        raise NotImplementedError()


class PWMMotorAdapter(MotorAdapter):
    """Backend-facing stub for the eventual GPIO/PWM motor implementation.

    The concrete hardware driver is intentionally injected because motor HAT
    selection and pin mapping are still undecided in this phase.
    """

    def __init__(self, backend: Optional[object] = None):
        self.backend = backend

    def _require_backend(self) -> object:
        if self.backend is None:
            raise RuntimeError("PWM motor backend is not configured")
        return self.backend

    def set_motion(self, linear_mps: float, angular_dps: float) -> None:
        backend = self._require_backend()
        drive = getattr(backend, "set_motion", None)
        if not callable(drive):
            raise RuntimeError("PWM motor backend does not implement set_motion")
        drive(linear_mps=linear_mps, angular_dps=angular_dps)

    def stop(self) -> None:
        backend = self._require_backend()
        stop = getattr(backend, "stop", None)
        if not callable(stop):
            raise RuntimeError("PWM motor backend does not implement stop")
        stop()


class MockMotorAdapter(MotorAdapter):
    """Mock drive adapter that records commanded motion for tests."""

    def __init__(self):
        self.commands: List[MotorCommand] = []
        self.stop_count = 0

    def set_motion(self, linear_mps: float, angular_dps: float) -> None:
        self.commands.append(MotorCommand(linear_mps=linear_mps, angular_dps=angular_dps))

    def stop(self) -> None:
        self.stop_count += 1


__all__ = ["MotorAdapter", "MotorCommand", "PWMMotorAdapter", "MockMotorAdapter"]