import pandas as pd
import pytest

from minidatadev.analysis.charts import create_chart
from minidatadev.analysis.operations import (
    AnalysisValidationError,
    calculate_correlation,
    compare_periods,
    describe_column,
    filter_data,
    find_outliers,
    group_and_aggregate,
    sort_data,
)
from minidatadev.analysis.validation import (
    AggregationRequest,
    ChartRequest,
    CorrelationRequest,
    DateComparisonRequest,
    DescribeColumnRequest,
    FilterCondition,
    FilterRequest,
    OutlierRequest,
    SortRequest,
)


@pytest.fixture
def sales() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [
                "2024-01-10",
                "2024-02-10",
                "2025-01-10",
                "2025-02-10",
            ],
            "region": ["North", "South", "North", "South"],
            "revenue": [100.0, 200.0, 80.0, 150.0],
            "units": [10, 20, 8, 15],
        }
    )


def test_filter_data_uses_validated_conditions(sales: pd.DataFrame) -> None:
    result = filter_data(
        sales,
        FilterRequest(
            conditions=(
                FilterCondition(column="region", operator="eq", value="North"),
                FilterCondition(column="revenue", operator="gte", value=90),
            )
        ),
    )

    assert result.table["revenue"].tolist() == [100.0]
    assert result.tool_name == "filter_data"
    assert "2 validated filter" in result.provenance[0]


def test_filter_rejects_unknown_column(sales: pd.DataFrame) -> None:
    request = FilterRequest(
        conditions=(
            FilterCondition(column="profit", operator="gt", value=0),
        )
    )

    with pytest.raises(AnalysisValidationError, match="Unknown column"):
        filter_data(sales, request)


def test_grouped_aggregation_is_numerically_correct(sales: pd.DataFrame) -> None:
    result = group_and_aggregate(
        sales,
        AggregationRequest(
            group_by=("region",),
            metric="revenue",
            operation="sum",
        ),
    )

    assert result.table.to_dict(orient="records") == [
        {"region": "South", "sum_revenue": 350.0},
        {"region": "North", "sum_revenue": 180.0},
    ]
    assert result.parameters["operation"] == "sum"


def test_aggregation_rejects_non_numeric_metric(sales: pd.DataFrame) -> None:
    with pytest.raises(AnalysisValidationError, match="must be numeric"):
        group_and_aggregate(
            sales,
            AggregationRequest(metric="region", operation="mean"),
        )


def test_sort_uses_matching_directions(sales: pd.DataFrame) -> None:
    result = sort_data(
        sales,
        SortRequest(columns=("region", "revenue"), directions=("asc", "desc")),
    )

    assert result.table.iloc[0]["revenue"] == 100
    assert result.table.iloc[-1]["revenue"] == 150


def test_correlation_returns_verified_matrix(sales: pd.DataFrame) -> None:
    result = calculate_correlation(
        sales,
        CorrelationRequest(columns=("revenue", "units")),
    )

    assert result.table.columns.tolist() == ["column", "revenue", "units"]
    assert result.table.loc[0, "revenue"] == pytest.approx(1.0)
    assert "revenue" in result.summary


def test_describe_column_returns_numeric_statistics(
    sales: pd.DataFrame,
) -> None:
    result = describe_column(
        sales,
        DescribeColumnRequest(column="revenue"),
    )

    statistics = result.table.set_index("statistic")["value"]
    assert statistics["mean"] == pytest.approx(132.5)
    assert statistics["missing"] == 0
    assert result.tool_name == "describe_column"


def test_outliers_uses_iqr_fences() -> None:
    frame = pd.DataFrame({"value": [1, 2, 3, 4, 100]})

    result = find_outliers(frame, OutlierRequest(column="value"))

    assert result.table["value"].tolist() == [100]
    assert "1 outliers" in result.summary


def test_period_comparison_calculates_group_declines(
    sales: pd.DataFrame,
) -> None:
    result = compare_periods(
        sales,
        DateComparisonRequest(
            date_column="date",
            metric="revenue",
            operation="sum",
            group_by="region",
            first_period="2024",
            second_period="2025",
        ),
    )

    north = result.table.loc[result.table["region"] == "North"].iloc[0]
    assert north["absolute_change"] == -20
    assert north["percent_change"] == pytest.approx(-20)
    assert result.assumptions


def test_chart_generation_returns_plotly_figure(sales: pd.DataFrame) -> None:
    result = create_chart(
        sales,
        ChartRequest(chart_type="bar", x="region", y="revenue"),
    )

    assert result.chart is not None
    assert result.chart.data[0].type == "bar"
    assert result.tool_name == "create_chart"
