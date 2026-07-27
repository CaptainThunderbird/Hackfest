import pandas as pd

from minidatadev.ai import ChatMessage, DatasetAssistant, DemoProvider
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


def test_demo_assistant_defers_verified_calculation_tools() -> None:
    answer, _ = _reply("Which region has the largest total sales?")

    assert "Phase 3" in answer
