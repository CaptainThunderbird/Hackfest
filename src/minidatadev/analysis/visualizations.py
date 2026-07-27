"""Type-aware chart recommendations and editable chart construction."""

import hashlib
from typing import Literal

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pydantic import BaseModel, ConfigDict

from minidatadev.analysis.operations import AnalysisValidationError
from minidatadev.analysis.profiling import DatasetProfile

ChartKind = Literal["bar", "line", "scatter", "histogram", "box"]
AggregationKind = Literal["sum", "mean", "median", "count", "none"]


class ChartRecommendation(BaseModel):
    """A chart configuration justified by detected column roles."""

    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    reason: str
    chart_type: ChartKind
    x: str
    y: str | None = None
    grouping: str | None = None
    aggregation: AggregationKind = "none"


def recommend_charts(
    profile: DatasetProfile,
    *,
    limit: int = 6,
) -> tuple[ChartRecommendation, ...]:
    """Return a small diverse set of explainable chart recommendations."""

    numeric = [item.name for item in profile.column_profiles if item.kind == "number"]
    categories = [
        item.name
        for item in profile.column_profiles
        if item.kind == "category"
    ]
    dates = [item.name for item in profile.column_profiles if item.kind == "date"]
    recommendations: list[ChartRecommendation] = []

    if categories and numeric:
        recommendations.append(
            _recommendation(
                title=f"{numeric[0]} by {categories[0]}",
                reason="Compare a numeric total across categories.",
                chart_type="bar",
                x=categories[0],
                y=numeric[0],
                aggregation="sum",
            )
        )
    if dates and numeric:
        recommendations.append(
            _recommendation(
                title=f"{numeric[0]} over time",
                reason="Reveal change and direction across the available dates.",
                chart_type="line",
                x=dates[0],
                y=numeric[0],
                aggregation="sum",
            )
        )
    if len(numeric) >= 2:
        recommendations.append(
            _recommendation(
                title=f"{numeric[0]} vs {numeric[1]}",
                reason="Inspect the relationship between two numeric columns.",
                chart_type="scatter",
                x=numeric[0],
                y=numeric[1],
            )
        )
    if numeric:
        recommendations.append(
            _recommendation(
                title=f"Distribution of {numeric[0]}",
                reason="See the range, concentration, and shape of numeric values.",
                chart_type="histogram",
                x=numeric[0],
            )
        )
        recommendations.append(
            _recommendation(
                title=f"Spread of {numeric[0]}",
                reason="Spot the median, range, and potential extreme values.",
                chart_type="box",
                x=numeric[0],
            )
        )
    if categories:
        recommendations.append(
            _recommendation(
                title=f"Records by {categories[0]}",
                reason="Compare how many records fall into each category.",
                chart_type="bar",
                x=categories[0],
                aggregation="count",
            )
        )
    return tuple(recommendations[:limit])


def build_chart(
    frame: pd.DataFrame,
    *,
    chart_type: ChartKind,
    x: str,
    y: str | None = None,
    grouping: str | None = None,
    aggregation: AggregationKind = "none",
    title: str | None = None,
) -> tuple[go.Figure, pd.DataFrame, dict]:
    """Build an editable chart and return its bounded explanatory context."""

    required = [x]
    if y:
        required.append(y)
    if grouping:
        required.append(grouping)
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise AnalysisValidationError(
            f"Unknown chart column(s): {', '.join(missing)}."
        )
    if chart_type in {"line", "scatter"} and y is None:
        raise AnalysisValidationError(f"A {chart_type} chart requires a y column.")
    if aggregation in {"sum", "mean", "median"}:
        if y is None or not pd.api.types.is_numeric_dtype(frame[y]):
            raise AnalysisValidationError(
                f"{aggregation.title()} aggregation requires a numeric y column."
            )

    chart_frame = _prepare_chart_frame(
        frame,
        x=x,
        y=y,
        grouping=grouping,
        aggregation=aggregation,
    )
    color = grouping if grouping and grouping in chart_frame.columns else None
    if chart_type == "bar":
        figure = px.bar(chart_frame, x=x, y=_value_column(y, aggregation), color=color)
    elif chart_type == "line":
        figure = px.line(
            chart_frame,
            x=x,
            y=_value_column(y, aggregation),
            color=color,
            markers=True,
        )
    elif chart_type == "scatter":
        figure = px.scatter(chart_frame, x=x, y=y, color=color)
    elif chart_type == "histogram":
        figure = px.histogram(chart_frame, x=x, color=color)
    else:
        figure = px.box(chart_frame, x=color, y=x if y is None else y, color=color)
    resolved_title = title or _default_title(chart_type, x, y, aggregation)
    figure.update_layout(
        title=resolved_title,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=55, b=10),
        legend_title_text=grouping,
    )
    context = chart_context(
        chart_frame,
        chart_type=chart_type,
        x=x,
        y=_value_column(y, aggregation),
        grouping=grouping,
        aggregation=aggregation,
        title=resolved_title,
    )
    return figure, chart_frame, context


def chart_context(
    chart_frame: pd.DataFrame,
    *,
    chart_type: str,
    x: str,
    y: str | None,
    grouping: str | None,
    aggregation: str,
    title: str,
) -> dict:
    """Create bounded facts used for chart-aware conversations."""

    context = {
        "title": title,
        "chart_type": chart_type,
        "x": x,
        "y": y,
        "grouping": grouping,
        "aggregation": aggregation,
        "points": len(chart_frame),
        "preview": chart_frame.head(12).where(chart_frame.notna(), None).to_dict(
            orient="records"
        ),
    }
    if y and y in chart_frame.columns and pd.api.types.is_numeric_dtype(chart_frame[y]):
        usable = chart_frame[[x, y]].dropna()
        if not usable.empty:
            highest = usable.loc[usable[y].idxmax()]
            lowest = usable.loc[usable[y].idxmin()]
            context["highest"] = {"label": str(highest[x]), "value": float(highest[y])}
            context["lowest"] = {"label": str(lowest[x]), "value": float(lowest[y])}
    return context


def explain_chart(context: dict) -> str:
    """Explain a chart strictly from its calculated bounded context."""

    opening = (
        f"**{context['title']}** is a {context['chart_type']} chart using "
        f"`{context['x']}`"
    )
    if context.get("y"):
        opening += f" and `{context['y']}`"
    opening += f", with {context['points']:,} plotted rows."
    details = []
    if context.get("aggregation") not in {None, "none"}:
        details.append(
            f"Values are aggregated with **{context['aggregation']}**."
        )
    if context.get("highest"):
        highest = context["highest"]
        details.append(
            f"The highest plotted value is **{highest['label']}** at "
            f"**{highest['value']:,.2f}**."
        )
    if context.get("lowest"):
        lowest = context["lowest"]
        details.append(
            f"The lowest plotted value is **{lowest['label']}** at "
            f"**{lowest['value']:,.2f}**."
        )
    details.append(
        "The chart describes the plotted data; it does not by itself "
        "establish causation."
    )
    return opening + "\n\n" + " ".join(details)


def _prepare_chart_frame(
    frame: pd.DataFrame,
    *,
    x: str,
    y: str | None,
    grouping: str | None,
    aggregation: AggregationKind,
) -> pd.DataFrame:
    if aggregation == "none":
        selected = list(dict.fromkeys(item for item in (x, y, grouping) if item))
        return frame[selected].dropna(subset=[x]).head(5000).copy()
    groups = list(dict.fromkeys(item for item in (x, grouping) if item))
    grouped = frame.groupby(groups, dropna=False, observed=True)
    if aggregation == "count":
        return grouped.size().rename("record_count").reset_index()
    return (
        grouped[y]
        .agg(aggregation)
        .rename(f"{aggregation}_{y}")
        .reset_index()
    )


def _value_column(y: str | None, aggregation: AggregationKind) -> str | None:
    if aggregation == "count":
        return "record_count"
    if aggregation != "none" and y:
        return f"{aggregation}_{y}"
    return y


def _default_title(
    chart_type: str,
    x: str,
    y: str | None,
    aggregation: str,
) -> str:
    if aggregation == "count":
        return f"Records by {x}"
    if y:
        prefix = f"{aggregation.title()} " if aggregation != "none" else ""
        return f"{prefix}{y} by {x}"
    return f"{chart_type.title()} of {x}"


def _recommendation(**kwargs) -> ChartRecommendation:
    signature = ":".join(str(kwargs.get(key)) for key in sorted(kwargs))
    identifier = hashlib.sha1(
        signature.encode(),
        usedforsecurity=False,
    ).hexdigest()[:12]
    return ChartRecommendation(id=identifier, **kwargs)
