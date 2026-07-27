"""Chat orchestration independent of Streamlit."""

from collections.abc import Iterator

import pandas as pd

from minidatadev.ai.context import build_dataset_context
from minidatadev.ai.models import ChatMessage, Usage
from minidatadev.ai.prompts import SYSTEM_PROMPT
from minidatadev.ai.providers import ChatProvider
from minidatadev.analysis import DatasetProfile


class DatasetAssistant:
    """Coordinate context construction and provider streaming."""

    def __init__(self, provider: ChatProvider):
        self.provider = provider

    @property
    def last_usage(self) -> Usage:
        return self.provider.last_usage

    def stream_reply(
        self,
        *,
        frame: pd.DataFrame,
        profile: DatasetProfile,
        dataset_name: str,
        messages: list[ChatMessage],
        session_context: dict | None = None,
    ) -> Iterator[str]:
        context = build_dataset_context(
            frame,
            profile,
            dataset_name=dataset_name,
            session_context=session_context,
        )
        return self.provider.stream(
            messages=messages,
            system_prompt=SYSTEM_PROMPT,
            dataset_context=context,
        )
