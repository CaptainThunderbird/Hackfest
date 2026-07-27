"""Streamlit session-state helpers kept independent of UI rendering."""

from collections.abc import MutableMapping
from typing import Any

DEFAULT_SESSION = {
    "active_dataset": None,
    "active_dataset_name": None,
    "dataset_profile": None,
    "chat_messages": [],
    "current_filters": [],
    "saved_charts": [],
    "definitions": {},
    "assumptions": [],
    "usage": {"input_tokens": 0, "output_tokens": 0, "requests": 0},
}


def initialize_session(state: MutableMapping[str, Any]) -> None:
    """Add missing MiniDataDev keys without overwriting existing state."""

    for key, value in DEFAULT_SESSION.items():
        if key not in state:
            state[key] = value.copy() if hasattr(value, "copy") else value


def set_active_dataset(
    state: MutableMapping[str, Any],
    *,
    frame: Any,
    name: str,
    profile: Any,
) -> None:
    """Activate a dataset and reset context that belongs to the previous one."""

    state["active_dataset"] = frame
    state["active_dataset_name"] = name
    state["dataset_profile"] = profile
    state["chat_messages"] = []
    state["current_filters"] = []
    state["saved_charts"] = []
    state["definitions"] = {}
    state["assumptions"] = []
