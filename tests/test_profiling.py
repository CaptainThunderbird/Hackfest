import pandas as pd

from minidatadev.analysis import profile_dataframe, profile_table


def test_profiles_shape_quality_and_column_semantics() -> None:
    frame = pd.DataFrame(
        {
            "region": ["North", "South", "North"],
            "revenue": [10.0, None, 30.0],
            "date": ["2026-01-01", "2026-01-02", "2026-01-03"],
        }
    )

    profile = profile_dataframe(frame)

    assert profile.rows == 3
    assert profile.columns == 3
    assert profile.missing_cells == 1
    assert profile.completeness_percent == 88.9
    assert [item.kind for item in profile.column_profiles] == [
        "category",
        "number",
        "date",
    ]
    assert profile.column_profiles[1].mean == 20.0


def test_profile_table_has_display_columns() -> None:
    profile = profile_dataframe(pd.DataFrame({"value": [1, 2]}))

    table = profile_table(profile)

    assert table.columns.tolist() == [
        "Column",
        "Type",
        "Storage type",
        "Complete",
        "Missing",
        "Missing %",
        "Unique",
    ]
