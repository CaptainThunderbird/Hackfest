"""Fast, deterministic dataframe profiling for the product shell."""

from datetime import date, datetime
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict

ColumnKind = Literal["number", "date", "boolean", "category", "text"]


class ColumnProfile(BaseModel):
    """A compact profile safe to display or include in assistant context."""

    model_config = ConfigDict(frozen=True)

    name: str
    dtype: str
    kind: ColumnKind
    non_null: int
    missing: int
    missing_percent: float
    unique: int
    minimum: str | float | int | None = None
    maximum: str | float | int | None = None
    mean: float | None = None
    examples: tuple[str, ...] = ()


class DatasetProfile(BaseModel):
    """Summary of a loaded dataframe."""

    model_config = ConfigDict(frozen=True)

    rows: int
    columns: int
    duplicate_rows: int
    memory_bytes: int
    missing_cells: int
    column_profiles: tuple[ColumnProfile, ...]

    @property
    def completeness_percent(self) -> float:
        cells = self.rows * self.columns
        return round(100 * (cells - self.missing_cells) / cells, 1) if cells else 100.0


def profile_dataframe(frame: pd.DataFrame) -> DatasetProfile:
    """Build a bounded profile without modifying the source dataframe."""

    columns = tuple(_profile_column(str(name), frame[name]) for name in frame.columns)
    return DatasetProfile(
        rows=len(frame),
        columns=len(frame.columns),
        duplicate_rows=int(frame.duplicated().sum()),
        memory_bytes=int(frame.memory_usage(index=True, deep=True).sum()),
        missing_cells=int(frame.isna().sum().sum()),
        column_profiles=columns,
    )


def profile_table(profile: DatasetProfile) -> pd.DataFrame:
    """Convert the profile to a display-friendly dataframe."""

    return pd.DataFrame(
        [
            {
                "Column": item.name,
                "Type": item.kind.title(),
                "Storage type": item.dtype,
                "Complete": item.non_null,
                "Missing": item.missing,
                "Missing %": item.missing_percent,
                "Unique": item.unique,
            }
            for item in profile.column_profiles
        ]
    )


def _profile_column(name: str, series: pd.Series) -> ColumnProfile:
    non_null = series.dropna()
    kind = _column_kind(series, non_null)
    missing = int(series.isna().sum())
    minimum: str | float | int | None = None
    maximum: str | float | int | None = None
    mean: float | None = None

    if kind == "number" and not non_null.empty:
        minimum = _scalar(non_null.min())
        maximum = _scalar(non_null.max())
        mean = round(float(non_null.mean()), 4)
    elif kind == "date" and not non_null.empty:
        parsed = pd.to_datetime(
            non_null,
            errors="coerce",
            format="mixed",
        ).dropna()
        if not parsed.empty:
            minimum = parsed.min().isoformat()
            maximum = parsed.max().isoformat()

    examples = tuple(
        str(value)[:80] for value in non_null.astype(str).drop_duplicates().head(3)
    )
    return ColumnProfile(
        name=name,
        dtype=str(series.dtype),
        kind=kind,
        non_null=int(series.notna().sum()),
        missing=missing,
        missing_percent=round(100 * missing / len(series), 1) if len(series) else 0,
        unique=int(non_null.nunique()),
        minimum=minimum,
        maximum=maximum,
        mean=mean,
        examples=examples,
    )


def _column_kind(series: pd.Series, non_null: pd.Series) -> ColumnKind:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "number"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"
    if not non_null.empty:
        parsed = pd.to_datetime(
            non_null.head(100),
            errors="coerce",
            format="mixed",
        )
        if float(parsed.notna().mean()) >= 0.9:
            return "date"
    unique = int(non_null.nunique())
    if unique <= min(50, max(10, int(len(non_null) * 0.2))):
        return "category"
    return "text"


def _scalar(value: Any) -> str | float | int | None:
    if pd.isna(value):
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (int, float, str)):
        return value
    return str(value)
