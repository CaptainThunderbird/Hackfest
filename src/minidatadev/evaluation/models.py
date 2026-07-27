"""Validated models for repeatable product evaluations."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CaseCategory = Literal[
    "numerical",
    "filter",
    "chart",
    "schema",
    "ambiguity",
    "safety",
    "malformed_data",
]


class EvaluationCase(BaseModel):
    """One benchmark question and its deterministic expectations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z0-9_]+$")
    category: CaseCategory
    question: str = Field(min_length=1)
    expected_tool: str | None = None
    expected_first_row: dict[str, Any] | None = None
    expected_contains: tuple[str, ...] = ()
    expected_error_contains: str | None = None
    expected_chart_type: str | None = None
    forbidden_contains: tuple[str, ...] = ()
    malformed_payload: str | None = None
    max_latency_ms: float = Field(default=1000, gt=0)


class EvaluationResult(BaseModel):
    """Observed result and grader outcomes for one case."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    category: CaseCategory
    passed: bool
    latency_ms: float
    observed_tool: str | None = None
    response: str = ""
    error: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float | None = None
    grades: dict[str, bool]


class PricingConfig(BaseModel):
    """Optional provider pricing used only when explicitly configured."""

    model_config = ConfigDict(frozen=True)

    input_per_million: float = Field(ge=0)
    output_per_million: float = Field(ge=0)

    def estimate(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens * self.input_per_million
            + output_tokens * self.output_per_million
        ) / 1_000_000


class EvaluationReport(BaseModel):
    """Aggregate benchmark report suitable for CI and trend tracking."""

    model_config = ConfigDict(frozen=True)

    generated_at: str
    dataset: str
    total_cases: int
    passed_cases: int
    pass_rate: float
    numerical_correctness: float
    tool_selection_accuracy: float
    chart_correctness: float
    unsupported_claim_rate: float
    recovery_rate: float
    safety_rate: float
    average_latency_ms: float
    p95_latency_ms: float
    total_input_tokens: int
    total_output_tokens: int
    estimated_cost: float | None
    pricing_configured: bool
    results: tuple[EvaluationResult, ...]
