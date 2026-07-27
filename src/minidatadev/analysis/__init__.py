"""Dataset profiling APIs."""

from minidatadev.analysis.insights import Insight, generate_insights, suggest_questions
from minidatadev.analysis.profiling import (
    ColumnProfile,
    DatasetProfile,
    profile_dataframe,
    profile_table,
)
from minidatadev.analysis.results import AnalysisResult
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
from minidatadev.analysis.visualizations import (
    ChartRecommendation,
    build_chart,
    explain_chart,
    recommend_charts,
)

__all__ = [
    "ColumnProfile",
    "DatasetProfile",
    "AnalysisResult",
    "ChartRecommendation",
    "Insight",
    "AggregationRequest",
    "ChartRequest",
    "CorrelationRequest",
    "DateComparisonRequest",
    "DescribeColumnRequest",
    "FilterCondition",
    "FilterRequest",
    "OutlierRequest",
    "SortRequest",
    "profile_dataframe",
    "profile_table",
    "build_chart",
    "explain_chart",
    "generate_insights",
    "recommend_charts",
    "suggest_questions",
]
