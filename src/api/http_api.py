"""HTTP API stub for local runtime control and observability.

This module provides a lightweight stdlib HTTP server with three endpoints:
- GET /health
- GET /state
- POST /command

The server is intended for local development and should be started with
loopback host defaults unless explicitly configured otherwise.
"""
from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class HttpApiServer:
    """Small wrapper around ThreadingHTTPServer for runtime integration."""

    def __init__(
        self,
        host: str,
        port: int,
        get_state: Callable[[], dict[str, Any]],
        handle_command_text: Callable[[str], dict[str, Any] | None],
        mode: str = "mock",
    ):
        self.host = host
        self.port = int(port)
        self._get_state = get_state
        self._handle_command_text = handle_command_text
        self._mode = mode
        self._started_at = time.monotonic()

        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def bound_port(self) -> int:
        if self._server is None:
            return self.port
        return int(self._server.server_address[1])

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt: str, *args) -> None:
                # Keep API tests and runtime console output clean.
                return

            def do_GET(self) -> None:
                if self.path == "/health":
                    _json_response(
                        self,
                        200,
                        {
                            "status": "ok",
                            "mode": server._mode,
                            "uptime_s": round(max(0.0, time.monotonic() - server._started_at), 3),
                        },
                    )
                    return

                if self.path == "/state":
                    _json_response(self, 200, {"status": "ok", "state": server._get_state()})
                    return

                _json_response(self, 404, {"status": "error", "error": "NOT_FOUND"})

            def do_POST(self) -> None:
                if self.path != "/command":
                    _json_response(self, 404, {"status": "error", "error": "NOT_FOUND"})
                    return

                length_header = self.headers.get("Content-Length", "0")
                try:
                    content_length = int(length_header)
                except ValueError:
                    content_length = 0

                raw_body = self.rfile.read(max(0, content_length))
                try:
                    payload = json.loads(raw_body.decode("utf-8") if raw_body else "{}")
                except json.JSONDecodeError:
                    _json_response(self, 400, {"status": "error", "error": "INVALID_JSON"})
                    return

                command = payload.get("command") if isinstance(payload, dict) else None
                if not isinstance(command, str) or not command.strip():
                    _json_response(
                        self,
                        400,
                        {"status": "error", "error": "INVALID_COMMAND", "details": "command must be a non-empty string"},
                    )
                    return

                outcome = server._handle_command_text(command.strip())
                if outcome is None:
                    _json_response(self, 500, {"status": "error", "error": "NO_OUTCOME"})
                    return

                _json_response(self, 200, {"status": "ok", "outcome": outcome})

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, name="http-api-server", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)


__all__ = ["HttpApiServer"]
