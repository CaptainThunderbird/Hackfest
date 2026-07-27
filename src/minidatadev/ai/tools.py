"""Controlled tool registry and conservative natural-language planner."""

import re
from collections.abc import Callable
from typing import Any

import pandas as pd

from minidatadev.analysis.charts import create_chart
from minidatadev.analysis.operations import (
    AnalysisValidationError,
    calculate_correlation,
    compare_periods,
    describe_column,
    filter_data,
    find_outliers,
    group_and_aggregate,
    preview_rows,
    sort_data,
)
from minidatadev.analysis.results import AnalysisResult
from minidatadev.analysis.validation import (
    AggregationRequest,
    ChartRequest,
    CorrelationRequest,
    DateComparisonRequest,
    DescribeColumnRequest,
    FilterRequest,
    OutlierRequest,
    SortRequest,
)

TOOL_SCHEMAS = {
    "filter_data": FilterRequest.model_json_schema(),
    "sort_data": SortRequest.model_json_schema(),
    "group_and_aggregate": AggregationRequest.model_json_schema(),
    "calculate_correlation": CorrelationRequest.model_json_schema(),
    "find_outliers": OutlierRequest.model_json_schema(),
    "describe_column": DescribeColumnRequest.model_json_schema(),
    "compare_periods": DateComparisonRequest.model_json_schema(),
    "create_chart": ChartRequest.model_json_schema(),
}

ToolFunction = Callable[[pd.DataFrame, Any], AnalysisResult]
TOOL_REGISTRY: dict[str, tuple[type, ToolFunction]] = {
    "filter_data": (FilterRequest, filter_data),
    "sort_data": (SortRequest, sort_data),
    "group_and_aggregate": (AggregationRequest, group_and_aggregate),
    "calculate_correlation": (CorrelationRequest, calculate_correlation),
    "find_outliers": (OutlierRequest, find_outliers),
    "describe_column": (DescribeColumnRequest, describe_column),
    "compare_periods": (DateComparisonRequest, compare_periods),
    "create_chart": (ChartRequest, create_chart),
}


def execute_tool(
    frame: pd.DataFrame,
    tool_name: str,
    arguments: dict[str, Any],
) -> AnalysisResult:
    """Validate and execute one approved tool call."""

    try:
        model, function = TOOL_REGISTRY[tool_name]
    except KeyError as error:
        raise AnalysisValidationError(
            f"Unknown analysis tool '{tool_name}'."
        ) from error
    request = model.model_validate(arguments)
    return function(frame, request)


class AnalysisPlanner:
    """Map common explicit analytical questions to approved tool calls.

    The planner deliberately returns ``None`` when intent or column mapping is
    unclear. This keeps ambiguous questions in the conversational clarification
    path instead of guessing.
    """

    def try_execute(
        self,
        frame: pd.DataFrame,
        question: str,
    ) -> AnalysisResult | None:
        normalized = _normalize(question)
        mentioned = _mentioned_columns(frame, normalized)
        numeric = [
            column
            for column in mentioned
            if pd.api.types.is_numeric_dtype(frame[column])
        ]
        non_numeric = [column for column in mentioned if column not in numeric]

        if any(
            term in normalized
            for term in ("describe", "summary of", "statistics for", "stats for")
        ):
            if len(mentioned) == 1:
                return describe_column(
                    frame,
                    DescribeColumnRequest(column=str(mentioned[0])),
                )
            if "column" in normalized or mentioned:
                raise AnalysisValidationError(
                    "Name exactly one column for a statistical summary."
                )

        if any(word in normalized for word in ("correlation", "correlated")):
            if len(numeric) < 2:
                raise AnalysisValidationError(
                    "Correlation needs at least two named numeric columns."
                )
            return calculate_correlation(
                frame,
                CorrelationRequest(columns=tuple(numeric)),
            )

        if any(word in normalized for word in ("outlier", "unusual value")):
            if len(numeric) != 1:
                raise AnalysisValidationError(
                    "Name one numeric column for outlier analysis."
                )
            return find_outliers(frame, OutlierRequest(column=numeric[0]))

        years = re.findall(r"\b(?:19|20)\d{2}\b", normalized)
        relative_quarter = "this quarter" in normalized
        comparison_intent = any(
            word in normalized
            for word in ("compare", "changed", "change", "decline", "increased")
        )
        if comparison_intent and (len(set(years)) >= 2 or relative_quarter):
            date_columns = [
                column
                for column in frame.columns
                if pd.api.types.is_datetime64_any_dtype(frame[column])
                or any(
                    token in _normalize(str(column))
                    for token in ("date", "year", "month", "time")
                )
            ]
            date_column = next(
                (column for column in mentioned if column in date_columns),
                date_columns[0] if len(date_columns) == 1 else None,
            )
            metric = next(
                (column for column in numeric if column != date_column),
                None,
            )
            group_by = next(
                (column for column in non_numeric if column != date_column),
                None,
            )
            if not date_column or not metric:
                raise AnalysisValidationError(
                    "A period comparison needs a date column and a numeric metric."
                )
            if relative_quarter:
                parsed_dates = pd.to_datetime(
                    frame[date_column],
                    errors="coerce",
                    format="mixed",
                ).dropna()
                if parsed_dates.empty:
                    raise AnalysisValidationError(
                        f"Column '{date_column}' has no usable dates."
                    )
                current_quarter = parsed_dates.max().to_period("Q")
                previous_quarter = current_quarter - 1
                periods = [
                    _period_range(previous_quarter),
                    _period_range(current_quarter),
                ]
            else:
                periods = sorted(set(years))[:2]
            operation = _aggregation_operation(normalized)
            if operation not in {"sum", "mean", "count"}:
                operation = "sum"
            result = compare_periods(
                frame,
                DateComparisonRequest(
                    date_column=str(date_column),
                    metric=str(metric),
                    operation=operation,
                    group_by=str(group_by) if group_by else None,
                    first_period=periods[0],
                    second_period=periods[1],
                ),
            )
            if relative_quarter:
                result.assumptions = [
                    (
                        "\"This quarter\" means the quarter containing the "
                        f"latest dataset date ({parsed_dates.max().date()}); "
                        "it is compared with the immediately preceding quarter."
                    )
                ]
            if _chart_intent(normalized):
                result.chart = _result_chart(result, group_by)
                result.provenance.append("Rendered the verified comparison as a chart.")
            return result

        aggregation_intent = any(
            word in normalized
            for word in (
                "total",
                "sum",
                "average",
                "mean",
                "median",
                "highest",
                "lowest",
                "maximum",
                "minimum",
                "count",
                "how many",
                " by ",
            )
        )
        if aggregation_intent:
            operation = _aggregation_operation(normalized)
            metric = _choose_metric(numeric, normalized, frame)
            group_by = _choose_group(mentioned, metric, normalized)
            if operation != "count" and metric is None:
                raise AnalysisValidationError(
                    "Name a numeric metric for this calculation."
                )
            if " by " in f" {normalized} " and group_by is None:
                raise AnalysisValidationError(
                    "Name the column to group the calculation by."
                )
            result = group_and_aggregate(
                frame,
                AggregationRequest(
                    group_by=(str(group_by),) if group_by else (),
                    metric=str(metric) if metric else None,
                    operation=operation,
                    sort="asc" if any(
                        word in normalized for word in ("lowest", "smallest", "decline")
                    ) else "desc",
                ),
            )
            if _chart_intent(normalized) and group_by:
                result.chart = _result_chart(result, str(group_by))
                result.provenance.append(
                    "Rendered the verified aggregation as a chart."
                )
            return result

        if _chart_intent(normalized):
            if not mentioned:
                raise AnalysisValidationError(
                    "Name the columns to use in the chart."
                )
            chart_type = _chart_type(normalized)
            x = non_numeric[0] if non_numeric else mentioned[0]
            y = next((column for column in numeric if column != x), None)
            return create_chart(
                frame,
                ChartRequest(
                    chart_type=chart_type,
                    x=str(x),
                    y=str(y) if y else None,
                ),
            )

        if any(term in normalized for term in ("preview", "show rows", "sample rows")):
            return preview_rows(frame, mentioned, 10)
        return None


def _mentioned_columns(frame: pd.DataFrame, normalized_question: str) -> list[str]:
    matches = []
    padded = f" {normalized_question} "
    for column in sorted(frame.columns, key=lambda item: len(str(item)), reverse=True):
        normalized_column = _normalize(str(column))
        if normalized_column and f" {normalized_column} " in padded:
            matches.append(column)
    return matches


def _choose_metric(
    numeric: list[str],
    question: str,
    frame: pd.DataFrame,
) -> str | None:
    del question, frame
    return numeric[0] if numeric else None


def _choose_group(
    mentioned: list[str],
    metric: str | None,
    question: str,
) -> str | None:
    if " by " not in f" {question} ":
        return None
    return next((column for column in mentioned if column != metric), None)


def _aggregation_operation(question: str) -> str:
    if any(word in question for word in ("average", "mean")):
        return "mean"
    if "median" in question:
        return "median"
    if any(word in question for word in ("minimum", "lowest", "smallest")):
        return "min" if " by " not in f" {question} " else "sum"
    if any(word in question for word in ("maximum", "highest", "largest")):
        return "max" if " by " not in f" {question} " else "sum"
    if any(word in question for word in ("count", "how many", "number of")):
        return "count"
    return "sum"


def _chart_intent(question: str) -> bool:
    return any(
        word in question
        for word in ("chart", "plot", "visualize", "visualise", "graph")
    )


def _chart_type(question: str) -> str:
    for chart_type in ("line", "scatter", "histogram", "box", "bar"):
        if chart_type in question:
            return chart_type
    return "bar"


def _result_chart(result: AnalysisResult, group_by: str | None):
    table = result.table
    if table is None or table.empty:
        return None
    numeric_columns = list(table.select_dtypes(include="number").columns)
    if group_by and group_by in table.columns and numeric_columns:
        chart_result = create_chart(
            table,
            ChartRequest(
                chart_type="bar",
                x=group_by,
                y=numeric_columns[0],
                title="Verified analysis result",
            ),
        )
        return chart_result.chart
    if "period" in table.columns and "value" in table.columns:
        return create_chart(
            table,
            ChartRequest(
                chart_type="bar",
                x="period",
                y="value",
                title="Period comparison",
            ),
        ).chart
    return None


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _period_range(period: pd.Period) -> str:
    start = period.start_time.date().isoformat()
    end = period.end_time.date().isoformat()
    return f"{start}:{end}"
