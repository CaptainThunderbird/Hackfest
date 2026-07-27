"""Offline-first evaluation runner for MiniDataDev reliability."""

import argparse
import json
import os
import statistics
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd

from minidatadev.ai import ChatMessage, DatasetAssistant, DemoProvider
from minidatadev.analysis import profile_dataframe
from minidatadev.analysis.operations import AnalysisValidationError
from minidatadev.data import DatasetLoader, DatasetLoadError
from minidatadev.evaluation.models import (
    EvaluationCase,
    EvaluationReport,
    EvaluationResult,
    PricingConfig,
)


class EvaluationRunner:
    """Run benchmark cases without requiring external AI credentials."""

    def __init__(
        self,
        *,
        frame: pd.DataFrame,
        dataset_name: str,
        cases: tuple[EvaluationCase, ...],
        pricing: PricingConfig | None = None,
    ):
        self.frame = frame
        self.dataset_name = dataset_name
        self.cases = cases
        self.pricing = pricing

    @classmethod
    def from_directory(cls, directory: str | Path) -> "EvaluationRunner":
        root = Path(directory)
        frame = pd.read_csv(root / "benchmark_sales.csv")
        raw_cases = json.loads((root / "cases.json").read_text(encoding="utf-8"))
        cases = tuple(EvaluationCase.model_validate(item) for item in raw_cases)
        return cls(
            frame=frame,
            dataset_name=str(root / "benchmark_sales.csv"),
            cases=cases,
            pricing=_pricing_from_environment(),
        )

    def run(self) -> EvaluationReport:
        results = tuple(self._run_case(case) for case in self.cases)
        latencies = [item.latency_ms for item in results]
        total_input = sum(item.input_tokens for item in results)
        total_output = sum(item.output_tokens for item in results)
        return EvaluationReport(
            generated_at=datetime.now(UTC).isoformat(),
            dataset=self.dataset_name,
            total_cases=len(results),
            passed_cases=sum(item.passed for item in results),
            pass_rate=_rate(item.passed for item in results),
            numerical_correctness=_grade_rate(results, "numerical_correctness"),
            tool_selection_accuracy=_grade_rate(results, "tool_selection"),
            chart_correctness=_grade_rate(results, "chart_correctness"),
            unsupported_claim_rate=1
            - _grade_rate(results, "claim_support"),
            recovery_rate=_grade_rate(results, "recovery"),
            safety_rate=_grade_rate(results, "safety"),
            average_latency_ms=round(statistics.fmean(latencies), 3)
            if latencies
            else 0,
            p95_latency_ms=round(_percentile(latencies, 0.95), 3),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            estimated_cost=(
                self.pricing.estimate(total_input, total_output)
                if self.pricing
                else None
            ),
            pricing_configured=self.pricing is not None,
            results=results,
        )

    def _run_case(self, case: EvaluationCase) -> EvaluationResult:
        started = perf_counter()
        if case.category == "malformed_data":
            return self._run_malformed_case(case, started)

        assistant = DatasetAssistant(DemoProvider())
        observed_tool = None
        response = ""
        error = None
        result = None
        try:
            result = assistant.analyze(frame=self.frame, question=case.question)
            if result is not None:
                observed_tool = result.tool_name
                response = result.summary
            else:
                profile = profile_dataframe(self.frame)
                response = "".join(
                    assistant.stream_reply(
                        frame=self.frame,
                        profile=profile,
                        dataset_name=self.dataset_name,
                        messages=[ChatMessage(role="user", content=case.question)],
                    )
                )
        except (AnalysisValidationError, ValueError) as caught:
            error = str(caught)
            response = error
        latency = (perf_counter() - started) * 1000
        usage = assistant.last_usage
        grades = _grade_case(
            case,
            result=result,
            observed_tool=observed_tool,
            response=response,
            error=error,
            latency_ms=latency,
        )
        return EvaluationResult(
            case_id=case.id,
            category=case.category,
            passed=all(grades.values()),
            latency_ms=round(latency, 3),
            observed_tool=observed_tool,
            response=response,
            error=error,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            estimated_cost=(
                self.pricing.estimate(usage.input_tokens, usage.output_tokens)
                if self.pricing
                else None
            ),
            grades=grades,
        )

    def _run_malformed_case(
        self,
        case: EvaluationCase,
        started: float,
    ) -> EvaluationResult:
        error = None
        try:
            DatasetLoader().load(
                BytesIO((case.malformed_payload or "").encode()),
                filename="malformed.csv",
            )
        except DatasetLoadError as caught:
            error = str(caught)
        latency = (perf_counter() - started) * 1000
        recovered = error is not None
        grades = {
            "numerical_correctness": True,
            "tool_selection": True,
            "chart_correctness": True,
            "claim_support": True,
            "recovery": recovered,
            "safety": True,
            "latency": latency <= case.max_latency_ms,
        }
        return EvaluationResult(
            case_id=case.id,
            category=case.category,
            passed=all(grades.values()),
            latency_ms=round(latency, 3),
            response=error or "Malformed data was unexpectedly accepted.",
            error=error,
            estimated_cost=0 if self.pricing else None,
            grades=grades,
        )


def _grade_case(
    case: EvaluationCase,
    *,
    result: Any,
    observed_tool: str | None,
    response: str,
    error: str | None,
    latency_ms: float,
) -> dict[str, bool]:
    expected_error = case.expected_error_contains
    numerical = _matches_first_row(
        result.table if result is not None else None,
        case.expected_first_row,
    )
    contains = all(
        expected.casefold() in response.casefold()
        for expected in case.expected_contains
    )
    tool_selection = (
        observed_tool == case.expected_tool
        if case.expected_tool is not None
        else True
    )
    chart_correct = (
        _chart_type(result) == case.expected_chart_type
        if case.expected_chart_type
        else True
    )
    recovery = (
        expected_error.casefold() in (error or "").casefold()
        if expected_error
        else error is None
    )
    forbidden_absent = all(
        phrase.casefold() not in response.casefold()
        for phrase in case.forbidden_contains
    )
    if result is not None:
        claim_support = bool(result.provenance)
    elif error is not None:
        claim_support = True
    elif case.expected_contains:
        claim_support = contains
    else:
        claim_support = case.category == "safety" and forbidden_absent
    return {
        "numerical_correctness": numerical and contains,
        "tool_selection": tool_selection,
        "chart_correctness": chart_correct,
        "claim_support": claim_support,
        "recovery": recovery,
        "safety": forbidden_absent and observed_tool not in {"run_python", "shell"},
        "latency": latency_ms <= case.max_latency_ms,
    }


def _matches_first_row(
    table: pd.DataFrame | None,
    expected: dict[str, Any] | None,
) -> bool:
    if expected is None:
        return True
    if table is None or table.empty:
        return False
    observed = table.iloc[0].to_dict()
    for key, value in expected.items():
        if key not in observed:
            return False
        if isinstance(value, float):
            if abs(float(observed[key]) - value) > 1e-8:
                return False
        elif observed[key] != value:
            return False
    return True


def _chart_type(result: Any) -> str | None:
    if result is None or result.chart is None or not result.chart.data:
        return None
    return str(result.chart.data[0].type)


def _rate(values) -> float:
    items = list(values)
    return round(sum(bool(item) for item in items) / len(items), 4) if items else 1


def _grade_rate(results: tuple[EvaluationResult, ...], grade: str) -> float:
    return _rate(item.grades[grade] for item in results)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * percentile) - 1))
    return ordered[index]


def _pricing_from_environment() -> PricingConfig | None:
    input_price = os.getenv("MINIDATADEV_INPUT_PRICE_PER_MILLION")
    output_price = os.getenv("MINIDATADEV_OUTPUT_PRICE_PER_MILLION")
    if input_price is None or output_price is None:
        return None
    return PricingConfig(
        input_per_million=float(input_price),
        output_per_million=float(output_price),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MiniDataDev reliability cases.")
    parser.add_argument(
        "--cases",
        default="tests/evaluation_cases",
        help="Directory containing cases.json and benchmark_sales.csv.",
    )
    parser.add_argument("--output", default="reports/evaluation.json")
    parser.add_argument("--minimum-pass-rate", type=float, default=1.0)
    arguments = parser.parse_args()
    report = EvaluationRunner.from_directory(arguments.cases).run()
    output = Path(arguments.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    print(
        f"{report.passed_cases}/{report.total_cases} cases passed "
        f"({report.pass_rate:.1%}); report: {output}"
    )
    return 0 if report.pass_rate >= arguments.minimum_pass_rate else 1


if __name__ == "__main__":
    raise SystemExit(main())
