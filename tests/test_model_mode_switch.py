from main import _build_llama_adapter


class _DummyLogger:
    def warning(self, *args, **kwargs):
        return None


def test_build_llama_adapter_mock_mode():
    llama, mode = _build_llama_adapter(
        model_mode="mock",
        model_path="",
        lib_path="",
        strict_model=False,
        logger=_DummyLogger(),
    )

    assert mode == "mock"
    out = llama.generate("hello")
    assert "mock response" in out


def test_build_llama_adapter_real_mode_without_model_path_falls_back_when_not_strict():
    llama, mode = _build_llama_adapter(
        model_mode="real",
        model_path="",
        lib_path="",
        strict_model=False,
        logger=_DummyLogger(),
    )

    assert mode == "mock"
    out = llama.generate("hello")
    assert "mock response" in out


def test_build_llama_adapter_real_mode_without_model_path_raises_when_strict():
    try:
        _build_llama_adapter(
            model_mode="real",
            model_path="",
            lib_path="",
            strict_model=True,
            logger=_DummyLogger(),
        )
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "MODEL_PATH" in str(exc)
