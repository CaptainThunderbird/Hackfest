"""Chat orchestration independent of Streamlit."""

from collections.abc import Iterator

import pandas as pd

from minidatadev.ai.context import build_dataset_context
from minidatadev.ai.models import ChatMessage, Usage
from minidatadev.ai.prompts import SYSTEM_PROMPT
from minidatadev.ai.providers import ChatProvider, ToolPlanningProvider
from minidatadev.ai.tools import AnalysisPlanner, execute_tool
from minidatadev.analysis import AnalysisResult, DatasetProfile


class DatasetAssistant:
    """Coordinate context construction and provider streaming."""

    def __init__(
        self,
        provider: ChatProvider,
        planner: AnalysisPlanner | None = None,
    ):
        self.provider = provider
        self.planner = planner or AnalysisPlanner()

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

    def analyze(
        self,
        *,
        frame: pd.DataFrame,
        question: str,
    ) -> AnalysisResult | None:
        """Attempt a verified calculation for supported analytical intent."""

        result = self.planner.try_execute(frame, question)
        if result is not None:
            return result
        if isinstance(self.provider, ToolPlanningProvider):
            columns = [
                {
                    "name": str(column),
                    "dtype": str(frame[column].dtype),
                }
                for column in frame.columns
            ]
            call = self.provider.plan_tool(
                question=question,
                columns=columns,
            )
            if call is not None:
                result = execute_tool(frame, call.name, call.arguments)
                result.provenance.insert(
                    0,
                    f"The AI selected the approved `{call.name}` tool.",
                )
                return result
        return None
