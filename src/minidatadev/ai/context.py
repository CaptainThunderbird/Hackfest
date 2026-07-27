"""Build bounded, schema-aware context from the active dataset."""

import json
from typing import Any

import pandas as pd

from minidatadev.analysis import DatasetProfile


def build_dataset_context(
    frame: pd.DataFrame,
    profile: DatasetProfile,
    *,
    dataset_name: str,
    session_context: dict[str, Any] | None = None,
) -> str:
    """Serialize a compact dataset description without sending the dataframe."""

    context = session_context or {}
    payload = {
        "dataset": dataset_name,
        "shape": {"rows": profile.rows, "columns": profile.columns},
        "quality": {
            "missing_cells": profile.missing_cells,
            "duplicate_rows": profile.duplicate_rows,
            "completeness_percent": profile.completeness_percent,
        },
        "columns": [
            {
                "name": item.name,
                "storage_type": item.dtype,
                "semantic_type": item.kind,
                "missing": item.missing,
                "unique": item.unique,
                "minimum": item.minimum,
                "maximum": item.maximum,
                "mean": item.mean,
                "examples": list(item.examples),
            }
            for item in profile.column_profiles
        ],
        "preview": _safe_preview(frame),
        "conversation_context": {
            "filters": context.get("current_filters", []),
            "definitions": context.get("definitions", {}),
            "assumptions": context.get("assumptions", []),
        },
    }
    return json.dumps(payload, ensure_ascii=True, default=str)


def _safe_preview(frame: pd.DataFrame) -> list[dict[str, Any]]:
    preview = frame.head(3).copy()
    preview = preview.where(preview.notna(), None)
    return [
        {str(key): _truncate(value) for key, value in row.items()}
        for row in preview.to_dict(orient="records")
    ]


def _truncate(value: Any) -> Any:
    if isinstance(value, str):
        return value[:120]
    return value
