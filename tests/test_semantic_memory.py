from src.memory.semantic_memory import HashingSemanticEncoder, InMemorySemanticBackend, SemanticMemoryIndex


class _SemanticTestEncoder:
    dimensions = 2

    def encode(self, texts):
        mapping = {
            "i enjoy masala chai\nnoted": [1.0, 0.0],
            "which beverage do i enjoy": [1.0, 0.0],
            "i enjoy espresso\nnoted": [0.0, 1.0],
        }
        return [mapping.get(str(text).lower(), [0.0, 0.0]) for text in texts]


def test_hashing_semantic_encoder_is_deterministic():
    encoder = HashingSemanticEncoder(dimensions=16)

    first, second = encoder.encode(["favorite drink is chai", "favorite drink is chai"])

    assert first == second
    assert len(first) == 16


def test_semantic_memory_index_scopes_results_by_user():
    index = SemanticMemoryIndex(
        encoder=_SemanticTestEncoder(),
        backend=InMemorySemanticBackend(dimensions=2),
        prefer_faiss=False,
    )

    index.add_turn(1, 7, "I enjoy masala chai", "noted")
    index.add_turn(2, 8, "I enjoy espresso", "noted")

    matches = index.search("Which beverage do I enjoy", user_id=7, limit=2)

    assert len(matches) == 1
    assert matches[0].turn_id == 1
    assert matches[0].user_text == "I enjoy masala chai"