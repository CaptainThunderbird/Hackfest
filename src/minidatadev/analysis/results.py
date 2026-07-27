"""Rich, verified outputs returned by analysis tools."""

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import plotly.graph_objects as go


@dataclass(slots=True)
class AnalysisResult:
    """A calculation result with display artifacts and an audit trail."""

    summary: str
    tool_name: str
    table: pd.DataFrame | None = None
    chart: go.Figure | None = None
    provenance: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)

    def artifact(self) -> dict[str, Any]:
        """Return the fields retained in Streamlit session state."""

        return {
            "tool_name": self.tool_name,
            "table": self.table,
            "chart": self.chart,
            "provenance": self.provenance,
            "assumptions": self.assumptions,
            "parameters": self.parameters,
        }
