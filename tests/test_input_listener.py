from src.audio_adapter import MockAudioAdapter, MockSpeechToTextAdapter
from src.input_listener import ConsoleInputListener, SpeechInputListener


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


def test_speech_listener_transcribes_audio_once():
    listener = SpeechInputListener(
        audio_adapter=MockAudioAdapter(),
        stt_adapter=MockSpeechToTextAdapter(response="dock now"),
        duration=1.5,
    )

    assert listener.poll_once() == "dock now"
    assert listener.take_error() is None


def test_speech_listener_ignores_blank_transcription():
    listener = SpeechInputListener(
        audio_adapter=MockAudioAdapter(),
        stt_adapter=MockSpeechToTextAdapter(response="   "),
    )

    assert listener.poll_once() is None
    assert listener.take_error() is None


def test_speech_listener_maps_runtime_error_to_stt_unavailable():
    class _UnavailableSpeechToTextAdapter:
        def transcribe(self, audio_data):
            raise RuntimeError("vosk unavailable")

    listener = SpeechInputListener(
        audio_adapter=MockAudioAdapter(),
        stt_adapter=_UnavailableSpeechToTextAdapter(),
    )

    assert listener.poll_once() is None
    assert listener.take_error() == "STT_UNAVAILABLE"
    assert listener.take_error() is None


def test_speech_listener_maps_timeout_to_stt_timeout():
    class _TimeoutSpeechToTextAdapter:
        def transcribe(self, audio_data):
            raise TimeoutError("stt timed out")

    listener = SpeechInputListener(
        audio_adapter=MockAudioAdapter(),
        stt_adapter=_TimeoutSpeechToTextAdapter(),
    )

    assert listener.poll_once() is None
    assert listener.take_error() == "STT_TIMEOUT"


def test_speech_listener_maps_unknown_failure_to_stt_error():
    class _BrokenAudioAdapter:
        def record(self, duration):
            raise ValueError("mic failure")

    listener = SpeechInputListener(
        audio_adapter=_BrokenAudioAdapter(),
        stt_adapter=MockSpeechToTextAdapter(response="ignored"),
    )

    assert listener.poll_once() is None
    assert listener.take_error() == "STT_ERROR"


def test_speech_listener_exports_in_module_namespace():
    assert SpeechInputListener is not None


def test_speech_listener_preserves_error_across_polls():
    """Error from a failed poll must survive a subsequent poll without take_error() being called."""

    class _UnavailableSpeechToTextAdapter:
        def transcribe(self, audio_data):
            raise RuntimeError("vosk unavailable")

    listener = SpeechInputListener(
        audio_adapter=MockAudioAdapter(),
        stt_adapter=_UnavailableSpeechToTextAdapter(),
    )

    assert listener.poll_once() is None  # sets _pending_error
    assert listener.poll_once() is None  # must NOT clear the previous error
    assert listener.take_error() == "STT_UNAVAILABLE"


def test_speech_listener_clears_error_on_successful_transcription():
    """A successful transcription must clear any previously pending error."""

    class _RecoveringSpeechToTextAdapter:
        def __init__(self):
            self._calls = 0

        def transcribe(self, audio_data):
            self._calls += 1
            if self._calls == 1:
                raise RuntimeError("first call fails")
            return "dock now"

    listener = SpeechInputListener(
        audio_adapter=MockAudioAdapter(),
        stt_adapter=_RecoveringSpeechToTextAdapter(),
    )

    assert listener.poll_once() is None  # sets _pending_error
    assert listener.poll_once() == "dock now"  # success clears the error
    assert listener.take_error() is None
