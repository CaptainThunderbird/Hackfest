import pandas as pd
import pytest

from minidatadev.analysis import (
    build_chart,
    explain_chart,
    profile_dataframe,
    recommend_charts,
)
from minidatadev.analysis.operations import AnalysisValidationError


@pytest.fixture
def sales() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2026-01-01", "2026-01-02", "2026-01-01"]
            ),
            "region": ["North", "South", "North"],
            "revenue": [10.0, 20.0, 15.0],
            "profit": [2.0, 4.0, 3.0],
        }
    )


def test_recommendations_cover_comparison_time_and_relationship(
    sales: pd.DataFrame,
) -> None:
    recommendations = recommend_charts(profile_dataframe(sales))
    chart_types = {item.chart_type for item in recommendations}

    assert {"bar", "line", "scatter", "histogram", "box"} <= chart_types
    assert all(item.reason for item in recommendations)


def test_build_chart_aggregates_and_creates_context(sales: pd.DataFrame) -> None:
    figure, table, context = build_chart(
        sales,
        chart_type="bar",
        x="region",
        y="revenue",
        aggregation="sum",
        title="Revenue by region",
    )

    assert table.to_dict(orient="records") == [
        {"region": "North", "sum_revenue": 25.0},
        {"region": "South", "sum_revenue": 20.0},
    ]
    assert figure.data[0].type == "bar"
    assert context["highest"] == {"label": "North", "value": 25.0}
    assert context["points"] == 2


def test_chart_explanation_uses_calculated_context(sales: pd.DataFrame) -> None:
    _, _, context = build_chart(
        sales,
        chart_type="bar",
        x="region",
        y="revenue",
        aggregation="mean",
        title="Average revenue",
    )

    explanation = explain_chart(context)

    assert "**Average revenue**" in explanation
    assert "Values are aggregated with **mean**" in explanation
    assert "highest plotted value" in explanation


def test_line_chart_requires_y_column(sales: pd.DataFrame) -> None:
    with pytest.raises(AnalysisValidationError, match="requires a y column"):
        build_chart(
            sales,
            chart_type="line",
            x="date",
        )


def test_numeric_aggregation_requires_numeric_y(sales: pd.DataFrame) -> None:
    with pytest.raises(AnalysisValidationError, match="numeric y column"):
        build_chart(
            sales,
            chart_type="bar",
            x="region",
            y="date",
            aggregation="sum",
        )
