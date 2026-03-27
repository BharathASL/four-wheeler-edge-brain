from src.memory.conversation_memory import ConversationMemoryStore, RetrievalBenchmarkRecorder
from src.memory.semantic_memory import InMemorySemanticBackend, SemanticMemoryIndex


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


def test_search_relevant_turns_hybrid_mode_backfills_after_semantic_dedupe(tmp_path):
    db_path = tmp_path / "memory.sqlite"

    class _DuplicateSemanticIndex:
        def __init__(self):
            self.max_indexed_turn_id = -1

        def add_turn(self, turn_id, user_id, user_text, assistant_text):
            self.max_indexed_turn_id = max(self.max_indexed_turn_id, int(turn_id))
            return True

        def add_turns_batch(self, turns):
            if turns:
                self.max_indexed_turn_id = max(self.max_indexed_turn_id, max(int(t[0]) for t in turns))
            return len(turns)

        def search(self, query, user_id, limit):
            return [
                type(
                    "Match",
                    (),
                    {
                        "user_text": "my favorite color is blue",
                        "assistant_text": "noted",
                    },
                )(),
                type(
                    "Match",
                    (),
                    {
                        "user_text": "my favorite color is blue",
                        "assistant_text": "noted",
                    },
                )(),
            ][:limit]

    store = ConversationMemoryStore(str(db_path), semantic_index=_DuplicateSemanticIndex())
    user_id, _ = store.get_or_create_user("alex")
    store.append_turn(user_id, "my favorite color is blue", "noted")
    store.append_turn(user_id, "my favorite drink is espresso", "noted")

    rows = store.search_relevant_turns(
        user_id=user_id,
        query="favorite",
        limit=2,
        retrieval_mode="hybrid",
    )

    assert len(rows) == 2
    assert rows[0]["user"] == "my favorite color is blue"
    assert rows[1]["user"] == "my favorite drink is espresso"


def test_hybrid_mode_metrics_marks_text_fallback_as_used_even_without_matches(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    semantic_index = SemanticMemoryIndex(
        encoder=_FakeEncoder(),
        backend=InMemorySemanticBackend(dimensions=3),
        prefer_faiss=False,
    )
    store = ConversationMemoryStore(str(db_path), semantic_index=semantic_index)
    recorder = RetrievalBenchmarkRecorder()

    user_id, _ = store.get_or_create_user("alex")
    store.append_turn(user_id, "I enjoy masala chai", "noted")

    rows = store.search_relevant_turns(
        user_id=user_id,
        query="query with no lexical overlap",
        limit=2,
        retrieval_mode="hybrid",
        metrics_hook=recorder.record,
    )

    assert rows
    summary = recorder.summary()
    assert summary["fts_usage_ratio"] == 1.0


def test_append_turn_stores_multiple_structured_slots(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    store = ConversationMemoryStore(str(db_path))

    user_id, _ = store.get_or_create_user("bharath")
    store.append_turn(
        user_id,
        "I have a dog named Pixel, I live in Bangalore, and I like Python programming.",
        "noted",
    )

    assert store.get_all_slots(user_id) == {
        "pet_name": "Pixel",
        "city": "Bangalore",
        "programming_language": "Python",
    }


def test_append_turn_applies_explicit_slot_correction(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    store = ConversationMemoryStore(str(db_path))

    user_id, _ = store.get_or_create_user("alex")
    store.append_turn(user_id, "My favorite color is blue.", "noted")
    store.append_turn(user_id, "Actually, change it to black.", "updated")

    assert store.get_slot(user_id, "favorite_color") == "black"


def test_append_turn_does_not_store_session_directives_as_slots(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    store = ConversationMemoryStore(str(db_path))

    user_id, _ = store.get_or_create_user("alex")
    store.append_turn(user_id, "Always respond in one sentence.", "okay")

    assert store.get_all_slots(user_id) == {}


def test_append_turn_stores_remembered_number_slot(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    store = ConversationMemoryStore(str(db_path))

    user_id, _ = store.get_or_create_user("alex")
    store.append_turn(user_id, "Remember this number: 4829317", "noted")

    assert store.get_slot(user_id, "remembered_number") == "4829317"


def test_append_turn_stores_food_preference_slot(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    store = ConversationMemoryStore(str(db_path))

    user_id, _ = store.get_or_create_user("alex")
    store.append_turn(user_id, "I like dosa on weekends.", "noted")

    assert store.get_slot(user_id, "favorite_food") == "dosa"


def test_append_turn_rejects_unsafe_multi_speaker_slot_storage(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    store = ConversationMemoryStore(str(db_path))

    user_id, _ = store.get_or_create_user("alex")
    store.append_turn(
        user_id,
        "User1: My name is Arun and I like chess. User2: My name is Priya and I like music.",
        "ignored",
    )

    assert store.get_all_slots(user_id) == {}


def test_append_turn_stores_name_and_project_in_separate_slots(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    store = ConversationMemoryStore(str(db_path))

    user_id, _ = store.get_or_create_user("bharath")
    store.append_turn(
        user_id,
        "My name is Bharath and I am building a robot with 4 wheels. Remember this for future conversations.",
        "noted",
    )

    assert store.get_all_slots(user_id) == {
        "name": "Bharath",
        "project_summary": "a robot with 4 wheels",
    }


def test_append_turn_stores_enjoy_eating_food_preference_slot(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    store = ConversationMemoryStore(str(db_path))

    user_id, _ = store.get_or_create_user("alex")
    store.append_turn(user_id, "I enjoy eating dosa on weekends.", "noted")

    assert store.get_slot(user_id, "favorite_food") == "dosa"
