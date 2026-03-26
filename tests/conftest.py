import os
import sys
import time

import pytest

# Ensure the repository root is on sys.path so tests can import the `src` package.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def poll_until(cond, timeout=2.0, poll=0.01):
    """Poll *cond* every *poll* seconds until it returns True or *timeout* expires.

    Returns True if *cond* became True within the deadline, False otherwise.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cond():
            return True
        time.sleep(poll)
    return False


@pytest.fixture
def poll():
    """Pytest fixture that exposes :func:`poll_until` to test functions."""
    return poll_until


