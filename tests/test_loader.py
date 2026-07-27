from io import BytesIO

import pandas as pd
import pytest

from minidatadev.data import DatasetLoader, DatasetLoadError


def test_loads_csv_upload_and_records_provenance() -> None:
    upload = BytesIO(b"category,sales\nBooks,12\nGames,20\n")

    frame = DatasetLoader().load(upload, filename="sales.csv")

    assert frame.to_dict(orient="records") == [
        {"category": "Books", "sales": 12},
        {"category": "Games", "sales": 20},
    ]
    assert frame.attrs["source_type"] == "upload"
    assert frame.attrs["source_name"] == "sales.csv"


def test_loads_excel_upload() -> None:
    upload = BytesIO()
    pd.DataFrame({"value": [1, 2]}).to_excel(upload, index=False)
    upload.seek(0)

    frame = DatasetLoader().load(upload, filename="values.xlsx")

    assert frame["value"].tolist() == [1, 2]


def test_rejects_unsupported_file_type() -> None:
    with pytest.raises(DatasetLoadError, match="Unsupported file type"):
        DatasetLoader().load(BytesIO(b"{}"), filename="data.json")


def test_requires_filename_for_anonymous_upload() -> None:
    with pytest.raises(DatasetLoadError, match="filename is required"):
        DatasetLoader().load(BytesIO(b"a\n1\n"))


def test_lists_registered_samples() -> None:
    datasets = DatasetLoader().list_datasets()

    assert "avengers" in datasets
    assert "college-majors" in datasets
