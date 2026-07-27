import pandas as pd

from minidatadev.projects import initialize_session, set_active_dataset


def test_initialize_session_preserves_existing_values() -> None:
    state = {"definitions": {"revenue": "sales"}}

    initialize_session(state)

    assert state["definitions"] == {"revenue": "sales"}
    assert state["chat_messages"] == []


def test_setting_dataset_resets_dataset_specific_context() -> None:
    state = {
        "chat_messages": [{"role": "user", "content": "old"}],
        "current_filters": ["year=2025"],
        "saved_charts": ["chart"],
        "definitions": {"revenue": "sales"},
        "assumptions": ["calendar year"],
    }
    frame = pd.DataFrame({"value": [1]})

    set_active_dataset(state, frame=frame, name="new.csv", profile="profile")

    assert state["active_dataset"] is frame
    assert state["active_dataset_name"] == "new.csv"
    assert state["chat_messages"] == []
    assert state["definitions"] == {}
