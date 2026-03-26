from src.input_listener import ConsoleInputListener


def test_console_listener_reads_command(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "dock now")
    listener = ConsoleInputListener(prompt="> ")
    assert listener.poll_once() == "dock now"


def test_console_listener_ignores_empty(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "   ")
    listener = ConsoleInputListener(prompt="> ")
    assert listener.poll_once() is None


def test_console_listener_maps_eof_to_exit(monkeypatch):
    def _raise_eof(prompt):
        raise EOFError()

    monkeypatch.setattr("builtins.input", _raise_eof)
    listener = ConsoleInputListener(prompt="> ")
    assert listener.poll_once() == "exit"
