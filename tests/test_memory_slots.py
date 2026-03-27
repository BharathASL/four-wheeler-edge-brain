from src.memory.memory_slots import (
    apply_slot_update,
    detect_session_directive,
    detect_unsafe_memory_input,
    extract_requested_slot_names,
    extract_slots_from_input,
)


def test_extract_slots_from_multi_fact_input_creates_individual_slots():
    slots = extract_slots_from_input(
        "I have a dog named Pixel, I live in Bangalore, and I like Python programming."
    )

    slot_map = {slot.name: slot.value for slot in slots}

    assert slot_map == {
        "pet_name": "Pixel",
        "city": "Bangalore",
        "programming_language": "Python",
    }


def test_apply_slot_update_overwrites_latest_target_slot():
    existing = {slot.name: slot for slot in extract_slots_from_input("My favorite color is blue.")}

    updated_slots = apply_slot_update("Actually, change it to black.", existing)

    assert len(updated_slots) == 1
    assert updated_slots[0].name == "favorite_color"
    assert updated_slots[0].value == "black"


def test_detect_session_directive_flags_response_style_input():
    assert detect_session_directive("Always respond in one sentence") == "response_style"
    assert detect_session_directive("My favorite color is blue") is None


def test_extract_slots_from_number_memory_uses_typed_slot():
    slots = extract_slots_from_input("Remember this number: 4829317")

    assert [(slot.name, slot.value) for slot in slots] == [("remembered_number", "4829317")]


def test_extract_requested_slot_names_supports_compound_recall_queries():
    requested = extract_requested_slot_names("What is my dog's name and where do I live?")

    assert requested == ["pet_name", "city"]


def test_extract_slots_from_food_preference_creates_typed_food_slot():
    slots = extract_slots_from_input("I like dosa on weekends.")

    assert [(slot.name, slot.value) for slot in slots] == [("favorite_food", "dosa")]


def test_extract_slots_from_unsafe_multi_speaker_input_returns_no_slots():
    text = "User1: My name is Arun and I like chess. User2: My name is Priya and I like music."

    assert detect_unsafe_memory_input(text) == "multi_speaker"
    assert extract_slots_from_input(text) == []


def test_extract_slots_from_name_and_project_statement_keeps_separate_slots():
    slots = extract_slots_from_input(
        "My name is Bharath and I am building a robot with 4 wheels. Remember this for future conversations."
    )

    assert {slot.name: slot.value for slot in slots} == {
        "name": "Bharath",
        "project_summary": "a robot with 4 wheels",
    }


def test_extract_slots_from_preference_statement_does_not_absorb_trailing_clause():
    slots = extract_slots_from_input("I prefer Python over Java and I like simple solutions.")

    assert {slot.name: slot.value for slot in slots} == {"programming_language": "Python"}


def test_extract_slots_from_enjoy_eating_statement_creates_food_slot():
    slots = extract_slots_from_input("I enjoy eating dosa on weekends.")

    assert [(slot.name, slot.value) for slot in slots] == [("favorite_food", "dosa")]