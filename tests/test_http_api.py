import json
import socket
import urllib.error
import urllib.request

from main import process_command_text
from src.core.action_executor import ActionExecutor
from src.core.decision_engine import DecisionEngine
from src.api.http_api import HttpApiServer
from src.core.state_manager import StateManager


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _http_get_json(url: str):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=2.0) as resp:
        assert resp.status == 200
        return json.loads(resp.read().decode("utf-8"))


def _http_post_json(url: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=2.0) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _create_server():
    state = StateManager()
    decision_engine = DecisionEngine()
    executor = ActionExecutor(state_manager=state)

    def handle_command_text(command: str):
        return process_command_text(command, state, decision_engine, executor)

    server = HttpApiServer(
        host="127.0.0.1",
        port=_free_port(),
        get_state=state.snapshot,
        handle_command_text=handle_command_text,
        mode="mock",
    )
    server.start()
    return server


def test_health_endpoint_returns_status_and_mode():
    server = _create_server()
    try:
        body = _http_get_json(f"http://127.0.0.1:{server.bound_port}/health")
        assert body["status"] == "ok"
        assert body["mode"] == "mock"
        assert isinstance(body["uptime_s"], (int, float))
    finally:
        server.stop()


def test_state_endpoint_returns_state_snapshot():
    server = _create_server()
    try:
        body = _http_get_json(f"http://127.0.0.1:{server.bound_port}/state")
        assert body["status"] == "ok"
        snap = body["state"]
        assert "battery_level" in snap
        assert "is_idle" in snap
        assert "last_command_ts" in snap
    finally:
        server.stop()


def test_post_command_returns_action_outcome():
    server = _create_server()
    try:
        status, body = _http_post_json(
            f"http://127.0.0.1:{server.bound_port}/command",
            {"command": "move forward"},
        )
        assert status == 200
        assert body["status"] == "ok"
        assert body["outcome"]["action"]["action"] == "MOVE"
        assert body["outcome"]["result"]["status"] == "ok"
    finally:
        server.stop()


def test_post_command_rejects_invalid_command_payload():
    server = _create_server()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{server.bound_port}/command",
            data=json.dumps({"command": ""}).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=2.0)
            assert False, "expected HTTPError for invalid command"
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
            payload = json.loads(exc.read().decode("utf-8"))
            assert payload["status"] == "error"
            assert payload["error"] == "INVALID_COMMAND"
    finally:
        server.stop()


def test_unknown_path_returns_404():
    server = _create_server()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{server.bound_port}/does-not-exist",
            method="GET",
        )
        try:
            urllib.request.urlopen(req, timeout=2.0)
            assert False, "expected HTTPError for unknown path"
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
            payload = json.loads(exc.read().decode("utf-8"))
            assert payload["error"] == "NOT_FOUND"
    finally:
        server.stop()


def test_invalid_json_returns_400():
    server = _create_server()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{server.bound_port}/command",
            data=b"{bad json",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=2.0)
            assert False, "expected HTTPError for invalid json"
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
            payload = json.loads(exc.read().decode("utf-8"))
            assert payload["status"] == "error"
            assert payload["error"] == "INVALID_JSON"
    finally:
        server.stop()
