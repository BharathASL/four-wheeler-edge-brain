from src.llama_adapter import MockLlamaAdapter, LlamaAdapter


class _FakeChatLlama:
    def create_chat_completion(self, messages, max_tokens=128):
        return {
            "choices": [
                {
                    "message": {
                        "content": "hello from chat"
                    }
                }
            ]
        }


class _FakePromptLlama:
    def __call__(self, prompt, max_tokens=128):
        return {"choices": [{"text": "hello from prompt"}]}


def test_mock_adapter_generate_chat():
    adapter = MockLlamaAdapter()
    adapter.load_model("mock")

    out = adapter.generate_chat([
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u"},
    ])

    assert "mock chat" in out


def test_llama_adapter_generate_chat_uses_chat_completion_when_available():
    adapter = LlamaAdapter()
    adapter._llm = _FakeChatLlama()

    out = adapter.generate_chat([
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u"},
    ])

    assert out == "hello from chat"


def test_llama_adapter_generate_chat_falls_back_to_prompt_mode():
    adapter = LlamaAdapter()
    adapter._llm = _FakePromptLlama()

    out = adapter.generate_chat([
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u"},
    ])

    assert "hello from prompt" in out
