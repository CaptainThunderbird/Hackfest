import pandas as pd
import pytest
from pydantic import ValidationError

from minidatadev.ai.tools import AnalysisPlanner, execute_tool
from minidatadev.analysis.operations import AnalysisValidationError


@pytest.fixture
def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order date": [
                "2024-01-01",
                "2024-02-01",
                "2025-01-01",
                "2025-02-01",
            ],
            "category": ["A", "B", "A", "B"],
            "sales": [100, 80, 70, 90],
            "profit": [20, 10, 5, 12],
        }
    )


def test_execute_tool_rejects_unknown_arguments(frame: pd.DataFrame) -> None:
    with pytest.raises(ValidationError, match="Extra inputs"):
        execute_tool(
            frame,
            "group_and_aggregate",
            {
                "group_by": ["category"],
                "metric": "sales",
                "operation": "sum",
                "python": "do_not_execute()",
            },
        )


def test_execute_tool_rejects_unknown_tool(frame: pd.DataFrame) -> None:
    with pytest.raises(AnalysisValidationError, match="Unknown analysis tool"):
        execute_tool(frame, "run_python", {"code": "pass"})


def test_planner_runs_grouped_total_and_chart(frame: pd.DataFrame) -> None:
    result = AnalysisPlanner().try_execute(
        frame,
        "Create a bar chart of total sales by category",
    )

    assert result is not None
    assert result.table.iloc[0].to_dict() == {
        "category": "A",
        "sum_sales": 170,
    }
    assert result.chart is not None


def test_planner_runs_period_comparison(frame: pd.DataFrame) -> None:
    result = AnalysisPlanner().try_execute(
        frame,
        "Which category had the biggest sales decline from 2024 to 2025 "
        "using order date?",
    )

    assert result is not None
    assert result.tool_name == "compare_periods"
    assert "**A**" in result.summary


def test_planner_interprets_this_quarter_from_latest_dataset_date() -> None:
    frame = pd.DataFrame(
        {
            "date": [
                "2025-10-10",
                "2025-10-11",
                "2026-01-10",
                "2026-01-11",
            ],
            "category": ["A", "B", "A", "B"],
            "sales": [100, 80, 60, 90],
        }
    )

    result = AnalysisPlanner().try_execute(
        frame,
        "Which category had the biggest sales decline this quarter?",
    )

    assert result is not None
    assert "**A**" in result.summary
    assert result.assumptions
    assert "latest dataset date (2026-01-11)" in result.assumptions[0]


def test_planner_runs_correlation(frame: pd.DataFrame) -> None:
    result = AnalysisPlanner().try_execute(
        frame,
        "Calculate correlation between sales and profit",
    )

    assert result is not None
    assert result.tool_name == "calculate_correlation"


def test_planner_describes_one_column(frame: pd.DataFrame) -> None:
    result = AnalysisPlanner().try_execute(
        frame,
        "Describe the sales column",
    )

    assert result is not None
    assert result.tool_name == "describe_column"
    assert "mean" in result.summary


def test_planner_requests_clarification_for_missing_metric(
    frame: pd.DataFrame,
) -> None:
    with pytest.raises(AnalysisValidationError, match="numeric metric"):
        AnalysisPlanner().try_execute(frame, "Show total by category")


def test_planner_ignores_non_analytical_question(frame: pd.DataFrame) -> None:
    assert (
        AnalysisPlanner().try_execute(frame, "What does this dataset describe?")
        is None
    )
