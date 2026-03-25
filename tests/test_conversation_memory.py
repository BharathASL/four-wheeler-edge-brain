from src.conversation_memory import ConversationMemoryStore


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
