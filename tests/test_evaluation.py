from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

from minidatadev.evaluation.models import EvaluationCase, PricingConfig
from minidatadev.evaluation.runner import EvaluationRunner

CASES = Path("tests/evaluation_cases")


def test_benchmark_suite_passes_all_cases() -> None:
    report = EvaluationRunner.from_directory(CASES).run()

    assert report.total_cases == 10
    assert report.passed_cases == 10
    assert report.pass_rate == 1.0
    assert report.numerical_correctness == 1.0
    assert report.tool_selection_accuracy == 1.0
    assert report.chart_correctness == 1.0
    assert report.unsupported_claim_rate == 0.0
    assert report.recovery_rate == 1.0
    assert report.safety_rate == 1.0
    assert report.p95_latency_ms < 1000
    assert report.pricing_configured is False


def test_report_serializes_for_ci_artifacts() -> None:
    report = EvaluationRunner.from_directory(CASES).run()

    serialized = report.model_dump_json()

    assert '"pass_rate":1.0' in serialized
    assert '"estimated_cost":null' in serialized


def test_pricing_estimates_cost_from_reported_tokens() -> None:
    pricing = PricingConfig(input_per_million=2.0, output_per_million=8.0)

    assert pricing.estimate(500_000, 250_000) == pytest.approx(3.0)


def test_case_schema_rejects_unknown_expectation_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs"):
        EvaluationCase.model_validate(
            {
                "id": "unsafe_case",
                "category": "safety",
                "question": "test",
                "execute_python": True,
            }
        )


def test_unsupported_claim_metric_detects_missing_expected_evidence() -> None:
    case = EvaluationCase(
        id="unsupported",
        category="schema",
        question="What does this dataset describe?",
        expected_contains=("a claim that is not present",),
    )
    report = EvaluationRunner(
        frame=pd.DataFrame({"value": [1, 2]}),
        dataset_name="test",
        cases=(case,),
    ).run()

    assert report.pass_rate == 0
    assert report.unsupported_claim_rate == 1
