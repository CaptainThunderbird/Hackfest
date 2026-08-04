"""Explicit, auditable dataframe cleaning operations."""

from dataclasses import dataclass
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

MissingStrategy = Literal["keep", "drop_rows", "fill"]


class DataCleaningError(ValueError):
    """Raised when a cleaning plan cannot be applied safely."""


class CleaningPlan(BaseModel):
    """Validated set of deliberate transformations for one dataframe."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    remove_duplicates: bool = False
    missing_strategy: MissingStrategy = "keep"
    columns: tuple[str, ...] = Field(default=())

    @model_validator(mode="after")
    def require_columns_for_missing_strategy(self) -> "CleaningPlan":
        if self.missing_strategy != "keep" and not self.columns:
            raise ValueError("Select at least one column for missing-value handling.")
        return self


@dataclass(frozen=True)
class CleaningResult:
    """Cleaned dataframe plus an exportable audit record."""

    frame: pd.DataFrame
    actions: tuple[str, ...]
    rows_before: int
    rows_after: int
    missing_before: int
    missing_after: int
    duplicates_removed: int
    missing_filled: int

    @property
    def rows_removed(self) -> int:
        return self.rows_before - self.rows_after

    @property
    def summary(self) -> str:
        details = "; ".join(self.actions) or "No changes were needed."
        return f"Cleaning complete: {details}"

    def audit_record(self) -> dict[str, object]:
        """Return JSON-serializable provenance for reports and session state."""

        return {
            "actions": list(self.actions),
            "rows_before": self.rows_before,
            "rows_after": self.rows_after,
            "rows_removed": self.rows_removed,
            "missing_before": self.missing_before,
            "missing_after": self.missing_after,
            "missing_filled": self.missing_filled,
            "duplicates_removed": self.duplicates_removed,
        }


def clean_dataframe(frame: pd.DataFrame, plan: CleaningPlan) -> CleaningResult:
    """Apply a validated cleaning plan without mutating the source dataframe."""

    _require_columns(frame, plan.columns)
    cleaned = frame.copy(deep=True)
    cleaned.attrs.update(frame.attrs)
    rows_before = len(frame)
    missing_before = int(frame.isna().sum().sum())
    actions: list[str] = []
    duplicates_removed = 0
    missing_filled = 0

    if plan.remove_duplicates:
        duplicates_removed = int(cleaned.duplicated().sum())
        cleaned = cleaned.drop_duplicates().copy()
        actions.append(f"removed {duplicates_removed:,} duplicate row(s)")

    if plan.missing_strategy == "drop_rows":
        before_drop = len(cleaned)
        cleaned = cleaned.dropna(subset=list(plan.columns)).copy()
        removed = before_drop - len(cleaned)
        actions.append(
            f"removed {removed:,} row(s) missing selected required values"
        )
    elif plan.missing_strategy == "fill":
        for column in plan.columns:
            missing_count = int(cleaned[column].isna().sum())
            if not missing_count:
                continue
            fill_value, method = _fill_value(cleaned[column], column)
            cleaned[column] = cleaned[column].fillna(fill_value)
            missing_filled += missing_count
            actions.append(
                f"filled {missing_count:,} missing value(s) in {column} with {method}"
            )

    return CleaningResult(
        frame=cleaned,
        actions=tuple(actions),
        rows_before=rows_before,
        rows_after=len(cleaned),
        missing_before=missing_before,
        missing_after=int(cleaned.isna().sum().sum()),
        duplicates_removed=duplicates_removed,
        missing_filled=missing_filled,
    )


def _fill_value(series: pd.Series, column: str) -> tuple[object, str]:
    usable = series.dropna()
    if usable.empty:
        raise DataCleaningError(
            f"Column '{column}' contains only missing values and cannot be filled "
            "without an explicit replacement value."
        )
    if pd.api.types.is_numeric_dtype(series):
        return usable.median(), "the median"
    modes = usable.mode(dropna=True)
    if modes.empty:
        raise DataCleaningError(f"Column '{column}' does not have a usable mode.")
    return modes.iloc[0], "the most frequent value"


def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
    unknown = [column for column in columns if column not in frame.columns]
    if unknown:
        raise DataCleaningError(f"Unknown cleaning column(s): {', '.join(unknown)}")
