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
    "saved_insights": [],
    "active_chart_context": None,
    "active_chart": None,
    "active_chart_data": None,
    "chart_signature": None,
    "definitions": {},
    "assumptions": [],
    "usage": {"input_tokens": 0, "output_tokens": 0, "requests": 0},
    "owner_name": "Local user",
    "active_project_id": None,
    "onboarding_complete": False,
    "request_limiter": None,
    "cleaning_history": [],
    "cleaning_notice": None,
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
    state["saved_insights"] = []
    state["active_chart_context"] = None
    state["active_chart"] = None
    state["active_chart_data"] = None
    state["chart_signature"] = None
    state["definitions"] = {}
    state["assumptions"] = []
    state["active_project_id"] = None
    state["cleaning_history"] = []
    state["cleaning_notice"] = None


def save_insight(
    state: MutableMapping[str, Any],
    insight: dict[str, Any],
) -> bool:
    """Save a dataset insight once and report whether it was newly added."""

    saved = state["saved_insights"]
    identifier = insight["id"]
    if any(item["id"] == identifier for item in saved):
        return False
    saved.append(insight)
    return True
