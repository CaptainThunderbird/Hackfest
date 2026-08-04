import pandas as pd
import pytest

from minidatadev.data import (
    CleaningPlan,
    DataCleaningError,
    clean_dataframe,
)


def test_removes_duplicates_and_drops_rows_missing_required_values() -> None:
    frame = pd.DataFrame(
        {
            "region": ["North", "North", "South", None],
            "revenue": [10.0, 10.0, None, 30.0],
        }
    )

    result = clean_dataframe(
        frame,
        CleaningPlan(
            remove_duplicates=True,
            missing_strategy="drop_rows",
            columns=("region", "revenue"),
        ),
    )

    assert result.frame.to_dict(orient="records") == [
        {"region": "North", "revenue": 10.0}
    ]
    assert result.duplicates_removed == 1
    assert result.rows_removed == 3
    assert len(frame) == 4


def test_fills_numeric_with_median_and_text_with_mode() -> None:
    frame = pd.DataFrame(
        {
            "score": [10.0, None, 30.0],
            "segment": ["A", None, "A"],
        }
    )

    result = clean_dataframe(
        frame,
        CleaningPlan(missing_strategy="fill", columns=("score", "segment")),
    )

    assert result.frame["score"].tolist() == [10.0, 20.0, 30.0]
    assert result.frame["segment"].tolist() == ["A", "A", "A"]
    assert result.missing_filled == 2
    assert result.missing_after == 0
    assert len(result.audit_record()["actions"]) == 2


def test_rejects_unknown_or_entirely_missing_fill_columns() -> None:
    frame = pd.DataFrame({"empty": [None, None]})

    with pytest.raises(DataCleaningError, match="Unknown cleaning column"):
        clean_dataframe(
            frame,
            CleaningPlan(missing_strategy="fill", columns=("missing",)),
        )
    with pytest.raises(DataCleaningError, match="only missing values"):
        clean_dataframe(
            frame,
            CleaningPlan(missing_strategy="fill", columns=("empty",)),
        )
