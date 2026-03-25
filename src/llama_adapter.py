"""Adapter for TinyLlama (`llama-cpp-python`) with a mock fallback for local tests.

Implements a small, well-documented interface so the Decision Engine can call
`load_model()` and `generate(prompt, max_tokens, timeout)` without depending
on the native runtime during unit tests.
"""
from typing import Optional
import concurrent.futures
import threading
import time


class LlamaAdapter:
    """Production adapter wrapping `llama-cpp-python`.

    Real implementation should import `llama_cpp` lazily and expose:
    - `load_model(path)`
    - `generate(prompt, max_tokens=128, timeout=None)` -> str
    """

    def __init__(self, lib_path: Optional[str] = None):
        self.lib_path = lib_path
        self.model = None
        self._llm = None
        self._llm_lock = threading.Lock()

    def load_model(self, model_path: str):
        # Real code: import llama_cpp and load the model using provided path.
        # Keep this method side-effect free for tests by mocking.
        self.model = model_path
        # Try to lazily load the runtime if available. If the native library
        # is not present (e.g., on Windows/CI), keep `self._llm` as None so
        # callers can detect that production runtime isn't available.
        try:
            with self._llm_lock:
                if self._llm is None:
                    from llama_cpp import Llama  # type: ignore
                    self._llm = Llama(model_path=model_path)
        except Exception:
            # Leave _llm as None; tests should use MockLlamaAdapter.
            self._llm = None

    def _call_model(self, prompt: str, max_tokens: int = 128) -> str:
        # Internal: call the underlying llama-cpp-python object and return text.
        if self._llm is None:
            raise RuntimeError("llama runtime not available")

        resp = self._llm(prompt, max_tokens=max_tokens)
        # Attempt to extract text in a few common response shapes.
        if isinstance(resp, dict):
            choices = resp.get("choices") or []
            if choices and isinstance(choices[0], dict) and "text" in choices[0]:
                return choices[0]["text"]
            # Fallback to stringifying the response
            return str(resp)
        return str(resp)

    def generate(self, prompt: str, max_tokens: int = 128, timeout: Optional[float] = None) -> str:
        """Generate text from the model with an optional timeout (seconds).

        If the native runtime isn't available this will raise `RuntimeError`.
        Timeout is enforced using a worker thread; the underlying call may
        continue running in the background if it cannot be interrupted.
        """
        if timeout is None:
            # Direct call (may raise RuntimeError if runtime missing)
            return self._call_model(prompt, max_tokens=max_tokens)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(self._call_model, prompt, max_tokens)
            try:
                return fut.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                raise TimeoutError("llama generate() timed out")
            except Exception:
                # Propagate runtime errors as-is
                raise


class MockLlamaAdapter(LlamaAdapter):
    """Simple mock that returns deterministic responses for unit tests."""

    def load_model(self, model_path: str):
        super().load_model(model_path)

    def generate(self, prompt: str, max_tokens: int = 128, timeout: Optional[float] = None) -> str:
        # Return a short deterministic reply useful for unit tests.
        return f"[mock response] echo: {prompt[:80]}"


__all__ = ["LlamaAdapter", "MockLlamaAdapter"]
