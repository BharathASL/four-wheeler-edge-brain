from src.conversation_memory import ConversationMemoryStore, RetrievalBenchmarkRecorder
from src.semantic_memory import InMemorySemanticBackend, SemanticMemoryIndex


class _FakeEncoder:
    dimensions = 3

    def encode(self, texts):
        mapping = {
            "i enjoy masala chai\nnoted": [1.0, 0.0, 0.0],
            "what drink do i like": [1.0, 0.0, 0.0],
            "i enjoy espresso\nnoted": [0.0, 1.0, 0.0],
            "what coffee do i enjoy": [0.0, 1.0, 0.0],
        }
        return [mapping.get(str(text).lower(), [0.0, 0.0, 1.0]) for text in texts]


def test_get_or_create_user(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    store = ConversationMemoryStore(str(db_path))

    user_id_1, is_new_1 = store.get_or_create_user("bharath")
    user_id_2, is_new_2 = store.get_or_create_user("bharath")

    assert is_new_1 is True
    assert is_new_2 is False
    assert user_id_1 == user_id_2


def test_recent_turns_are_ordered_and_limited(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    store = ConversationMemoryStore(str(db_path))

    user_id, _ = store.get_or_create_user("alex")
    store.append_turn(user_id, "u1", "a1")
    store.append_turn(user_id, "u2", "a2")
    store.append_turn(user_id, "u3", "a3")

    turns = store.get_recent_turns(user_id, limit=2)

    assert turns == [
        {"user": "u2", "assistant": "a2"},
        {"user": "u3", "assistant": "a3"},
    ]


def test_search_relevant_turns_and_metrics_hook(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    store = ConversationMemoryStore(str(db_path))
    recorder = RetrievalBenchmarkRecorder()

    user_id, _ = store.get_or_create_user("alex")
    store.append_turn(user_id, "my favorite color is blue", "noted")
    store.append_turn(user_id, "i love robotics", "great")
    store.append_turn(user_id, "remind me to buy milk", "okay")

    rows = store.search_relevant_turns(
        user_id=user_id,
        query="favorite color",
        limit=2,
        metrics_hook=recorder.record,
    )

    assert rows
    assert any("favorite color" in turn["user"] for turn in rows)

    summary = recorder.summary()
    assert summary["queries"] == 1
    assert summary["avg_latency_ms"] >= 0
    assert summary["avg_returned_count"] >= 1


def test_search_relevant_turns_limit_zero(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    store = ConversationMemoryStore(str(db_path))

    user_id, _ = store.get_or_create_user("sam")
    store.append_turn(user_id, "hello world", "hi")

    rows = store.search_relevant_turns(user_id=user_id, query="hello", limit=0)
    assert rows == []


def test_search_relevant_turns_dinner_memory_query(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    store = ConversationMemoryStore(str(db_path))

    user_id, _ = store.get_or_create_user("bharath")
    store.append_turn(user_id, "we discussed robotics milestones", "noted")
    store.append_turn(user_id, "i had dosa for dinner", "thanks for sharing")

    rows = store.search_relevant_turns(
        user_id=user_id,
        query="Do you remember what I had for the dinner?",
        limit=1,
    )

    assert rows
    assert "dinner" in rows[0]["user"].lower()


def test_search_relevant_turns_prefers_newer_matching_fact(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    store = ConversationMemoryStore(str(db_path))

    user_id, _ = store.get_or_create_user("alex")
    store.append_turn(user_id, "my favorite color is blue", "noted")
    store.append_turn(user_id, "my favorite color is green", "updated")

    rows = store.search_relevant_turns(
        user_id=user_id,
        query="favorite color",
        limit=2,
    )

    assert rows
    assert rows[0]["user"] == "my favorite color is green"


def test_search_relevant_turns_is_scoped_to_each_user_across_sessions(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    store = ConversationMemoryStore(str(db_path))

    alex_id, _ = store.get_or_create_user("alex")
    sam_id, _ = store.get_or_create_user("sam")
    store.append_turn(alex_id, "my favorite color is green", "updated")
    store.append_turn(sam_id, "my favorite color is red", "noted")
    store.append_turn(alex_id, "i had dosa for dinner", "nice")

    alex_rows = store.search_relevant_turns(user_id=alex_id, query="favorite color", limit=2)
    sam_rows = store.search_relevant_turns(user_id=sam_id, query="favorite color", limit=2)

    assert alex_rows
    assert sam_rows
    assert all("green" in row["user"] or "dosa" in row["user"] for row in alex_rows)
    assert all("red" in row["user"] for row in sam_rows)


def test_search_relevant_turns_semantic_mode_uses_semantic_index(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    semantic_index = SemanticMemoryIndex(
        encoder=_FakeEncoder(),
        backend=InMemorySemanticBackend(dimensions=3),
        prefer_faiss=False,
    )
    store = ConversationMemoryStore(str(db_path), semantic_index=semantic_index)

    user_id, _ = store.get_or_create_user("alex")
    store.append_turn(user_id, "I enjoy masala chai", "noted")
    store.append_turn(user_id, "I enjoy espresso", "noted")

    rows = store.search_relevant_turns(
        user_id=user_id,
        query="What drink do I like",
        limit=1,
        retrieval_mode="semantic",
    )

    assert rows == [{"user": "I enjoy masala chai", "assistant": "noted"}]


def test_search_relevant_turns_hybrid_mode_falls_back_to_lexical_when_needed(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    semantic_index = SemanticMemoryIndex(
        encoder=_FakeEncoder(),
        backend=InMemorySemanticBackend(dimensions=3),
        prefer_faiss=False,
    )
    store = ConversationMemoryStore(str(db_path), semantic_index=semantic_index)

    user_id, _ = store.get_or_create_user("alex")
    store.append_turn(user_id, "my favorite color is blue", "noted")
    store.append_turn(user_id, "I enjoy espresso", "noted")

    rows = store.search_relevant_turns(
        user_id=user_id,
        query="favorite color",
        limit=2,
        retrieval_mode="hybrid",
    )

    assert rows
    assert rows[0]["user"] == "my favorite color is blue"
