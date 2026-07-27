"""Approved dataframe calculations with schema and type validation."""

from collections.abc import Iterable

import numpy as np
import pandas as pd

from minidatadev.analysis.results import AnalysisResult
from minidatadev.analysis.validation import (
    AggregationRequest,
    CorrelationRequest,
    DateComparisonRequest,
    DescribeColumnRequest,
    FilterCondition,
    FilterRequest,
    OutlierRequest,
    SortRequest,
)


class AnalysisValidationError(ValueError):
    """Raised when a requested operation is unsafe or incompatible."""


def filter_data(frame: pd.DataFrame, request: FilterRequest) -> AnalysisResult:
    """Filter rows using an allowlist of vectorized operators."""

    _require_columns(frame, [item.column for item in request.conditions])
    masks = [_condition_mask(frame[item.column], item) for item in request.conditions]
    mask = masks[0]
    for candidate in masks[1:]:
        mask = mask & candidate if request.combine == "and" else mask | candidate
    columns = list(request.columns) if request.columns else list(frame.columns)
    _require_columns(frame, columns)
    result = frame.loc[mask, columns].head(request.limit).copy()
    return AnalysisResult(
        summary=(
            f"Found **{int(mask.sum()):,} matching rows** out of "
            f"{len(frame):,}. Showing up to {request.limit:,}."
        ),
        tool_name="filter_data",
        table=result,
        provenance=[
            f"Evaluated {len(request.conditions)} validated filter condition(s).",
            f"Combined conditions with {request.combine.upper()}.",
            f"Selected {int(mask.sum()):,} of {len(frame):,} rows.",
        ],
        parameters=request.model_dump(mode="json"),
    )


def sort_data(frame: pd.DataFrame, request: SortRequest) -> AnalysisResult:
    """Sort rows by validated columns and directions."""

    _require_columns(frame, request.columns)
    directions = list(request.directions)
    if len(directions) == 1:
        directions *= len(request.columns)
    if len(directions) != len(request.columns):
        raise AnalysisValidationError(
            "Provide one sort direction or one direction per sort column."
        )
    result = frame.sort_values(
        list(request.columns),
        ascending=[item == "asc" for item in directions],
        na_position="last",
    ).head(request.limit)
    return AnalysisResult(
        summary=f"Sorted the dataset by **{', '.join(request.columns)}**.",
        tool_name="sort_data",
        table=result,
        provenance=[
            f"Sorted {len(frame):,} rows by {', '.join(request.columns)}.",
            f"Returned the first {min(len(result), request.limit):,} rows.",
        ],
        parameters=request.model_dump(mode="json"),
    )


def group_and_aggregate(
    frame: pd.DataFrame,
    request: AggregationRequest,
) -> AnalysisResult:
    """Perform a grouped or whole-dataset aggregation."""

    _require_columns(frame, request.group_by)
    if request.metric:
        _require_columns(frame, [request.metric])
    if request.operation in {"sum", "mean", "median", "min", "max"}:
        _require_numeric(frame, request.metric)

    output_name = (
        f"{request.operation}_{request.metric}"
        if request.metric
        else "row_count"
    )
    if request.group_by:
        grouped = frame.groupby(
            list(request.group_by),
            dropna=False,
            observed=True,
        )
        if request.operation == "count" and request.metric is None:
            result = grouped.size().rename(output_name).reset_index()
        else:
            result = (
                grouped[request.metric]
                .agg(request.operation)
                .rename(output_name)
                .reset_index()
            )
        result = result.sort_values(
            output_name,
            ascending=request.sort == "asc",
            na_position="last",
        ).head(request.limit)
        leader = result.iloc[0]
        group_label = ", ".join(
            f"{column}={leader[column]}" for column in request.group_by
        )
        value = _format_number(leader[output_name])
        summary = (
            f"**{group_label}** ranks first with **{value}** "
            f"for `{output_name}`."
        )
    else:
        if request.operation == "count":
            value = (
                len(frame)
                if request.metric is None
                else frame[request.metric].count()
            )
        else:
            value = getattr(frame[request.metric], request.operation)()
        result = pd.DataFrame({output_name: [value]})
        summary = f"The verified `{output_name}` is **{_format_number(value)}**."

    provenance = [
        f"Used {len(frame):,} input rows.",
        (
            f"Grouped by {', '.join(request.group_by)}."
            if request.group_by
            else "Calculated across the full dataset."
        ),
        f"Applied the {request.operation.upper()} aggregation.",
    ]
    return AnalysisResult(
        summary=summary,
        tool_name="group_and_aggregate",
        table=result,
        provenance=provenance,
        parameters=request.model_dump(mode="json"),
    )


def calculate_correlation(
    frame: pd.DataFrame,
    request: CorrelationRequest,
) -> AnalysisResult:
    """Calculate a correlation matrix for numeric columns."""

    _require_columns(frame, request.columns)
    for column in request.columns:
        _require_numeric(frame, column)
    result = frame[list(request.columns)].corr(method=request.method)
    pair = _strongest_pair(result)
    if pair:
        first, second, value = pair
        summary = (
            f"The strongest relationship is **{first} ↔ {second}** at "
            f"**{value:.3f}** ({request.method})."
        )
    else:
        summary = "There are not enough usable values to calculate a correlation."
    return AnalysisResult(
        summary=summary,
        tool_name="calculate_correlation",
        table=result.reset_index(names="column"),
        provenance=[
            f"Selected {len(request.columns)} validated numeric columns.",
            f"Calculated the {request.method.title()} correlation matrix.",
            "Pairwise missing values were excluded by Pandas.",
        ],
        parameters=request.model_dump(mode="json"),
    )


def describe_column(
    frame: pd.DataFrame,
    request: DescribeColumnRequest,
) -> AnalysisResult:
    """Return verified descriptive statistics for one column."""

    _require_columns(frame, [request.column])
    series = frame[request.column]
    base = [
        {"statistic": "rows", "value": len(series)},
        {"statistic": "non_null", "value": int(series.notna().sum())},
        {"statistic": "missing", "value": int(series.isna().sum())},
        {"statistic": "unique", "value": int(series.nunique(dropna=True))},
    ]
    if pd.api.types.is_numeric_dtype(series):
        description = series.describe(percentiles=[0.25, 0.5, 0.75])
        base.extend(
            {"statistic": str(statistic), "value": value}
            for statistic, value in description.items()
            if statistic not in {"count"}
        )
        summary = (
            f"`{request.column}` has a mean of "
            f"**{_format_number(series.mean())}** across "
            f"{series.notna().sum():,} usable values."
        )
    else:
        counts = series.fillna("<missing>").value_counts().head(request.top_values)
        base.extend(
            {
                "statistic": f"value: {value}",
                "value": int(count),
            }
            for value, count in counts.items()
        )
        top = counts.index[0] if not counts.empty else "not available"
        summary = (
            f"`{request.column}` contains **{series.nunique(dropna=True):,} "
            f"unique values**; the most frequent is **{top}**."
        )
    return AnalysisResult(
        summary=summary,
        tool_name="describe_column",
        table=pd.DataFrame(base),
        provenance=[
            f"Validated column `{request.column}`.",
            "Calculated descriptive statistics with Pandas.",
            "Missing values were reported separately from usable values.",
        ],
        parameters=request.model_dump(mode="json"),
    )


def find_outliers(frame: pd.DataFrame, request: OutlierRequest) -> AnalysisResult:
    """Find numeric outliers using IQR fences or z-scores."""

    _require_columns(frame, [request.column])
    _require_numeric(frame, request.column)
    series = frame[request.column]
    if request.method == "iqr":
        q1, q3 = series.quantile([0.25, 0.75])
        spread = q3 - q1
        lower = q1 - request.threshold * spread
        upper = q3 + request.threshold * spread
        mask = (series < lower) | (series > upper)
        method_detail = f"IQR fences [{lower:.4g}, {upper:.4g}]"
    else:
        standard_deviation = series.std(ddof=0)
        if not standard_deviation or pd.isna(standard_deviation):
            mask = pd.Series(False, index=frame.index)
        else:
            zscore = (series - series.mean()).abs() / standard_deviation
            mask = zscore > request.threshold
        method_detail = f"absolute z-score > {request.threshold:g}"
    result = frame.loc[mask].head(request.limit).copy()
    return AnalysisResult(
        summary=(
            f"Found **{int(mask.sum()):,} outliers** in `{request.column}` "
            f"using {method_detail}."
        ),
        tool_name="find_outliers",
        table=result,
        provenance=[
            f"Validated `{request.column}` as numeric.",
            f"Applied {method_detail}.",
            f"Flagged {int(mask.sum()):,} of {series.notna().sum():,} non-null values.",
        ],
        parameters=request.model_dump(mode="json"),
    )


def compare_periods(
    frame: pd.DataFrame,
    request: DateComparisonRequest,
) -> AnalysisResult:
    """Compare a metric between two calendar years or date ranges."""

    required = [request.date_column, request.metric]
    if request.group_by:
        required.append(request.group_by)
    _require_columns(frame, required)
    if request.operation in {"sum", "mean"}:
        _require_numeric(frame, request.metric)
    dates = pd.to_datetime(frame[request.date_column], errors="coerce", format="mixed")
    first_mask = _period_mask(dates, request.first_period)
    second_mask = _period_mask(dates, request.second_period)
    first = _period_aggregate(frame.loc[first_mask], request)
    second = _period_aggregate(frame.loc[second_mask], request)

    if request.group_by:
        result = first.merge(
            second,
            on=request.group_by,
            how="outer",
            suffixes=(f"_{request.first_period}", f"_{request.second_period}"),
        ).fillna(0)
        first_value = f"value_{request.first_period}"
        second_value = f"value_{request.second_period}"
        result["absolute_change"] = result[second_value] - result[first_value]
        result["percent_change"] = _safe_percent_change(
            result[first_value],
            result[second_value],
        )
        result = result.sort_values("absolute_change")
        weakest = result.iloc[0]
        summary = (
            f"**{weakest[request.group_by]}** had the largest decline: "
            f"**{_format_number(weakest['absolute_change'])}** "
            f"({weakest['percent_change']:.1f}%)."
        )
    else:
        first_value = float(first.iloc[0]["value"])
        second_value = float(second.iloc[0]["value"])
        change = second_value - first_value
        percent = (
            change / abs(first_value) * 100 if first_value else float("nan")
        )
        result = pd.DataFrame(
            {
                "period": [request.first_period, request.second_period],
                "value": [first_value, second_value],
            }
        )
        summary = (
            f"`{request.metric}` changed by **{_format_number(change)}** "
            f"({percent:.1f}%) from {request.first_period} to "
            f"{request.second_period}."
        )
    return AnalysisResult(
        summary=summary,
        tool_name="compare_periods",
        table=result,
        provenance=[
            f"Parsed `{request.date_column}` as dates.",
            f"Selected periods {request.first_period} and {request.second_period}.",
            f"Applied {request.operation.upper()} to `{request.metric}`.",
        ],
        assumptions=["Periods are interpreted as calendar years when given as YYYY."],
        parameters=request.model_dump(mode="json"),
    )


def preview_rows(
    frame: pd.DataFrame,
    columns: Iterable[str] = (),
    limit: int = 10,
) -> AnalysisResult:
    """Return a bounded preview of selected columns."""

    selected = list(columns) or list(frame.columns)
    _require_columns(frame, selected)
    limit = min(max(limit, 1), 100)
    return AnalysisResult(
        summary=f"Showing the first **{min(limit, len(frame)):,} rows**.",
        tool_name="preview_rows",
        table=frame[selected].head(limit).copy(),
        provenance=[
            f"Selected {len(selected)} validated columns.",
            f"Returned at most {limit} rows without modifying the dataset.",
        ],
        parameters={"columns": selected, "limit": limit},
    )


def _condition_mask(series: pd.Series, condition: FilterCondition) -> pd.Series:
    operator = condition.operator
    value = condition.value
    if operator == "eq":
        return series == value
    if operator == "ne":
        return series != value
    if operator == "gt":
        return series > value
    if operator == "gte":
        return series >= value
    if operator == "lt":
        return series < value
    if operator == "lte":
        return series <= value
    if operator == "contains":
        return series.astype("string").str.contains(
            str(value),
            case=False,
            regex=False,
            na=False,
        )
    if operator in {"in", "not_in"}:
        values = value if isinstance(value, (list, tuple, set)) else [value]
        mask = series.isin(values)
        return ~mask if operator == "not_in" else mask
    if operator == "is_null":
        return series.isna()
    return series.notna()


def _require_columns(frame: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        available = ", ".join(str(item) for item in frame.columns)
        raise AnalysisValidationError(
            f"Unknown column(s): {', '.join(missing)}. Available: {available}"
        )


def _require_numeric(frame: pd.DataFrame, column: str | None) -> None:
    if column is None or not pd.api.types.is_numeric_dtype(frame[column]):
        raise AnalysisValidationError(f"Column '{column}' must be numeric.")


def _strongest_pair(matrix: pd.DataFrame) -> tuple[str, str, float] | None:
    masked = matrix.where(~np.eye(len(matrix), dtype=bool))
    stacked = masked.abs().stack()
    if stacked.empty:
        return None
    first, second = stacked.idxmax()
    return str(first), str(second), float(matrix.loc[first, second])


def _period_mask(dates: pd.Series, period: str) -> pd.Series:
    if len(period) == 4 and period.isdigit():
        return dates.dt.year == int(period)
    try:
        start_text, end_text = period.split(":", maxsplit=1)
        start = pd.Timestamp(start_text)
        end = pd.Timestamp(end_text)
    except (ValueError, TypeError) as error:
        raise AnalysisValidationError(
            "Periods must be YYYY or start:end date ranges."
        ) from error
    return dates.between(start, end, inclusive="both")


def _period_aggregate(
    frame: pd.DataFrame,
    request: DateComparisonRequest,
) -> pd.DataFrame:
    if request.group_by:
        grouped = frame.groupby(request.group_by, dropna=False, observed=True)
        if request.operation == "count":
            values = grouped.size()
        else:
            values = grouped[request.metric].agg(request.operation)
        return values.rename("value").reset_index()
    if request.operation == "count":
        value = len(frame)
    else:
        value = getattr(frame[request.metric], request.operation)()
    return pd.DataFrame({"value": [value]})


def _safe_percent_change(first: pd.Series, second: pd.Series) -> pd.Series:
    result = (second - first) / first.abs().replace(0, np.nan) * 100
    return result.replace([np.inf, -np.inf], np.nan)


def _format_number(value: object) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if pd.isna(numeric):
        return "not available"
    if numeric.is_integer():
        return f"{int(numeric):,}"
    return f"{numeric:,.2f}"
