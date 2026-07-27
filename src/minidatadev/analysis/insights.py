"""Automatic, evidence-backed dataset observations and question suggestions."""

import hashlib
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict

from minidatadev.analysis.profiling import DatasetProfile


class Insight(BaseModel):
    """One concise automatic observation backed by calculated evidence."""

    model_config = ConfigDict(frozen=True)

    id: str
    kind: Literal["quality", "distribution", "relationship", "structure"]
    level: Literal["info", "opportunity", "warning"]
    title: str
    detail: str
    evidence: str
    suggested_question: str | None = None


def generate_insights(
    frame: pd.DataFrame,
    profile: DatasetProfile,
    *,
    limit: int = 8,
) -> tuple[Insight, ...]:
    """Generate deterministic observations without model-authored claims."""

    insights: list[Insight] = []
    if profile.missing_cells:
        affected = sorted(
            (
                item
                for item in profile.column_profiles
                if item.missing
            ),
            key=lambda item: item.missing_percent,
            reverse=True,
        )
        worst = affected[0]
        insights.append(
            _insight(
                "quality",
                "warning" if worst.missing_percent >= 20 else "opportunity",
                f"Missing values concentrate in {worst.name}",
                (
                    f"{worst.name} has {worst.missing:,} missing values "
                    f"({worst.missing_percent:.1f}%)."
                ),
                (
                    f"{profile.missing_cells:,} missing cells across "
                    f"{len(affected)} columns"
                ),
                f"Explain missing values in {worst.name}",
            )
        )
    else:
        insights.append(
            _insight(
                "quality",
                "info",
                "No missing values detected",
                "Every cell in the active dataset is populated.",
                f"{profile.rows * profile.columns:,} complete cells",
            )
        )

    if profile.duplicate_rows:
        percent = 100 * profile.duplicate_rows / profile.rows if profile.rows else 0
        insights.append(
            _insight(
                "quality",
                "warning",
                "Duplicate rows may affect totals",
                (
                    f"{profile.duplicate_rows:,} rows exactly duplicate another "
                    "record and may inflate aggregate results."
                ),
                f"{percent:.1f}% of rows are duplicates",
            )
        )

    for column in profile.column_profiles:
        if column.unique <= 1 and column.non_null:
            insights.append(
                _insight(
                    "structure",
                    "opportunity",
                    f"{column.name} is constant",
                    "This column does not vary and may add little analytical value.",
                    f"{column.unique} unique non-null value",
                )
            )

    numeric_columns = [
        item.name for item in profile.column_profiles if item.kind == "number"
    ]
    for column in numeric_columns:
        series = frame[column].dropna()
        if len(series) >= 8 and series.std() not in (0, None):
            skew = float(series.skew())
            if abs(skew) >= 1.5:
                direction = "right" if skew > 0 else "left"
                insights.append(
                    _insight(
                        "distribution",
                        "opportunity",
                        f"{column} is strongly {direction}-skewed",
                        (
                            "The average may not represent a typical value well; "
                            "compare it with the median."
                        ),
                        f"Skewness = {skew:.2f}",
                        f"Describe the {column} column",
                    )
                )

    if len(numeric_columns) >= 2:
        correlations = frame[numeric_columns].corr().abs()
        pairs = correlations.where(
            ~pd.DataFrame(
                [
                    [row == column for column in correlations.columns]
                    for row in correlations.index
                ],
                index=correlations.index,
                columns=correlations.columns,
            )
        ).stack()
        if not pairs.empty:
            first, second = pairs.idxmax()
            value = float(correlations.loc[first, second])
            if value >= 0.7:
                insights.append(
                    _insight(
                        "relationship",
                        "opportunity",
                        f"{first} and {second} move together",
                        (
                            "These columns have a strong linear relationship. "
                            "Correlation does not by itself establish causation."
                        ),
                        f"Absolute Pearson correlation = {value:.2f}",
                        f"Calculate correlation between {first} and {second}",
                    )
                )

    date_columns = [
        item for item in profile.column_profiles if item.kind == "date"
    ]
    for column in date_columns[:1]:
        if column.minimum and column.maximum:
            insights.append(
                _insight(
                    "structure",
                    "info",
                    f"{column.name} supports time comparisons",
                    (
                        f"The dataset spans {column.minimum[:10]} through "
                        f"{column.maximum[:10]}."
                    ),
                    "Date range inferred from non-null values",
                    f"How did the main metric change over {column.name}?",
                )
            )
    return tuple(insights[:limit])


def suggest_questions(profile: DatasetProfile, *, limit: int = 6) -> tuple[str, ...]:
    """Recommend answerable questions based on detected column roles."""

    numeric = [item.name for item in profile.column_profiles if item.kind == "number"]
    categories = [
        item.name
        for item in profile.column_profiles
        if item.kind == "category"
    ]
    dates = [item.name for item in profile.column_profiles if item.kind == "date"]
    questions = ["Which columns have missing values?"]
    if numeric:
        questions.append(f"Describe the {numeric[0]} column")
        questions.append(f"Find outliers in {numeric[0]}")
    if numeric and categories:
        questions.append(f"Show total {numeric[0]} by {categories[0]}")
        questions.append(
            f"Create a bar chart of total {numeric[0]} by {categories[0]}"
        )
    if len(numeric) >= 2:
        questions.append(
            f"Calculate correlation between {numeric[0]} and {numeric[1]}"
        )
    if dates and numeric:
        questions.append(
            f"How did {numeric[0]} change over {dates[0]}?"
        )
    return tuple(dict.fromkeys(questions))[:limit]


def _insight(
    kind: str,
    level: str,
    title: str,
    detail: str,
    evidence: str,
    suggested_question: str | None = None,
) -> Insight:
    identifier = hashlib.sha1(
        f"{kind}:{title}:{evidence}".encode(), usedforsecurity=False
    ).hexdigest()[:12]
    return Insight(
        id=identifier,
        kind=kind,
        level=level,
        title=title,
        detail=detail,
        evidence=evidence,
        suggested_question=suggested_question,
    )
