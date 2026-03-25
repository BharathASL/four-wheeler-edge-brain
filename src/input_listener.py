"""Input listener interfaces for Phase-1.

Separates command input concerns from orchestration logic so future backends
(STT, sockets, HTTP) can reuse the same contract.
"""
from typing import Callable, Optional


class InputListener:
    def poll_once(self) -> Optional[str]:
        """Return one command string, or None if there is no command."""
        raise NotImplementedError()


class ConsoleInputListener(InputListener):
    def __init__(self, prompt: str = "> "):
        self.prompt = prompt

    def poll_once(self) -> Optional[str]:
        try:
            raw = input(self.prompt)
        except EOFError:
            return "exit"
        text = raw.strip()
        if not text:
            return None
        return text

    def listen_forever(self, on_command: Callable[[str], None]) -> None:
        """Read commands indefinitely and forward them to a callback."""
        while True:
            cmd = self.poll_once()
            if cmd is None:
                continue
            on_command(cmd)


__all__ = ["InputListener", "ConsoleInputListener"]
