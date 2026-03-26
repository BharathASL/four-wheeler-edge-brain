from src.conversation_memory import ConversationMemoryStore, RetrievalBenchmarkRecorder


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
