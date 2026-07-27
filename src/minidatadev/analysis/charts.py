"""Validated Plotly chart generation."""

import pandas as pd
import plotly.express as px

from minidatadev.analysis.operations import (
    AnalysisValidationError,
    _require_columns,
)
from minidatadev.analysis.results import AnalysisResult
from minidatadev.analysis.validation import ChartRequest


def create_chart(frame: pd.DataFrame, request: ChartRequest) -> AnalysisResult:
    """Create an allowlisted Plotly chart using validated columns."""

    required = [request.x]
    if request.y:
        required.append(request.y)
    if request.grouping:
        required.append(request.grouping)
    _require_columns(frame, required)

    common = {
        "data_frame": frame,
        "x": request.x,
        "color": request.grouping,
        "title": request.title,
    }
    if request.chart_type == "bar":
        figure = px.bar(y=request.y, **common)
    elif request.chart_type == "line":
        if request.y is None:
            raise AnalysisValidationError("A line chart requires a y column.")
        figure = px.line(y=request.y, markers=True, **common)
    elif request.chart_type == "scatter":
        if request.y is None:
            raise AnalysisValidationError("A scatter chart requires a y column.")
        figure = px.scatter(y=request.y, **common)
    elif request.chart_type == "histogram":
        figure = px.histogram(**common)
    else:
        figure = px.box(y=request.y, **common)
    figure.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=50, b=10),
        legend_title_text=request.grouping,
    )
    return AnalysisResult(
        summary=f"Created a verified **{request.chart_type} chart**.",
        tool_name="create_chart",
        chart=figure,
        provenance=[
            f"Validated chart type `{request.chart_type}`.",
            f"Mapped x to `{request.x}`"
            + (f" and y to `{request.y}`." if request.y else "."),
            "Rendered with Plotly without executing generated code.",
        ],
        parameters=request.model_dump(mode="json"),
    )
