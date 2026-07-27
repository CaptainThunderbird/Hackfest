from collections.abc import Iterator

import pandas as pd

from minidatadev.ai import (
    ChatMessage,
    DatasetAssistant,
    DemoProvider,
    ToolCall,
    Usage,
)
from minidatadev.analysis import profile_dataframe


def _reply(question: str) -> tuple[str, DatasetAssistant]:
    frame = pd.DataFrame({"region": ["North", "South"], "sales": [10, None]})
    assistant = DatasetAssistant(DemoProvider())
    answer = "".join(
        assistant.stream_reply(
            frame=frame,
            profile=profile_dataframe(frame),
            dataset_name="sales.csv",
            messages=[ChatMessage(role="user", content=question)],
        )
    )
    return answer, assistant


def test_demo_assistant_answers_schema_questions() -> None:
    answer, assistant = _reply("Which columns are available?")

    assert "**region**" in answer
    assert "**sales**" in answer
    assert assistant.last_usage.requests == 1


def test_demo_assistant_reports_missing_values() -> None:
    answer, _ = _reply("Where are values missing?")

    assert "**sales**: 1 missing" in answer


def test_assistant_runs_verified_calculation_before_provider() -> None:
    frame = pd.DataFrame(
        {"region": ["North", "South", "North"], "sales": [10, 25, 20]}
    )
    assistant = DatasetAssistant(DemoProvider())

    result = assistant.analyze(
        frame=frame,
        question="Show total sales by region",
    )

    assert result is not None
    assert result.tool_name == "group_and_aggregate"
    assert result.table.iloc[0].to_dict() == {
        "region": "North",
        "sum_sales": 30,
    }
    assert assistant.last_usage.requests == 0


class PlanningProvider:
    name = "test"

    @property
    def last_usage(self) -> Usage:
        return Usage(requests=1)

    def stream(self, **kwargs) -> Iterator[str]:
        del kwargs
        yield "unused"

    def plan_tool(self, *, question, columns) -> ToolCall:
        del question, columns
        return ToolCall(
            name="group_and_aggregate",
            arguments={
                "group_by": ["region"],
                "metric": "sales",
                "operation": "mean",
            },
        )


def test_assistant_validates_provider_selected_tool() -> None:
    frame = pd.DataFrame(
        {"region": ["North", "North", "South"], "sales": [10, 20, 9]}
    )
    assistant = DatasetAssistant(PlanningProvider())

    result = assistant.analyze(
        frame=frame,
        question="Give me a provider-selected calculation",
    )

    assert result is not None
    assert result.table.iloc[0].to_dict() == {
        "region": "North",
        "mean_sales": 15.0,
    }
    assert result.provenance[0].startswith("The AI selected")
