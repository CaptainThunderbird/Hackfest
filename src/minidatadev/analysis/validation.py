"""Validated request schemas for approved dataframe operations."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FilterOperator = Literal[
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
    "contains",
    "in",
    "not_in",
    "is_null",
    "not_null",
]
Aggregation = Literal["sum", "mean", "median", "min", "max", "count", "nunique"]
SortDirection = Literal["asc", "desc"]
ChartType = Literal["bar", "line", "scatter", "histogram", "box"]


class StrictRequest(BaseModel):
    """Base request that rejects unknown model-supplied fields."""

    model_config = ConfigDict(extra="forbid")


class FilterCondition(StrictRequest):
    column: str = Field(min_length=1)
    operator: FilterOperator
    value: Any = None

    @model_validator(mode="after")
    def require_value_when_needed(self) -> "FilterCondition":
        if self.operator not in {"is_null", "not_null"} and self.value is None:
            raise ValueError(f"operator '{self.operator}' requires a value")
        return self


class FilterRequest(StrictRequest):
    conditions: tuple[FilterCondition, ...] = Field(min_length=1)
    combine: Literal["and", "or"] = "and"
    columns: tuple[str, ...] = ()
    limit: int = Field(default=100, ge=1, le=1000)


class SortRequest(StrictRequest):
    columns: tuple[str, ...] = Field(min_length=1)
    directions: tuple[SortDirection, ...] = ("asc",)
    limit: int = Field(default=100, ge=1, le=1000)


class AggregationRequest(StrictRequest):
    group_by: tuple[str, ...] = ()
    metric: str | None = None
    operation: Aggregation
    sort: SortDirection = "desc"
    limit: int = Field(default=20, ge=1, le=200)

    @model_validator(mode="after")
    def validate_metric_requirement(self) -> "AggregationRequest":
        if self.operation != "count" and not self.metric:
            raise ValueError(f"operation '{self.operation}' requires a metric")
        return self


class CorrelationRequest(StrictRequest):
    columns: tuple[str, ...] = Field(min_length=2, max_length=20)
    method: Literal["pearson", "spearman", "kendall"] = "pearson"


class OutlierRequest(StrictRequest):
    column: str = Field(min_length=1)
    method: Literal["iqr", "zscore"] = "iqr"
    threshold: float = Field(default=1.5, gt=0, le=10)
    limit: int = Field(default=100, ge=1, le=1000)


class DescribeColumnRequest(StrictRequest):
    column: str = Field(min_length=1)
    top_values: int = Field(default=10, ge=1, le=50)


class DateComparisonRequest(StrictRequest):
    date_column: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    operation: Literal["sum", "mean", "count"] = "sum"
    group_by: str | None = None
    first_period: str = Field(min_length=4)
    second_period: str = Field(min_length=4)


class ChartRequest(StrictRequest):
    chart_type: ChartType
    x: str = Field(min_length=1)
    y: str | None = None
    grouping: str | None = None
    title: str | None = None
