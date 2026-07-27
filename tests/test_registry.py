import pytest

from minidatadev.data import DatasetRegistry


def test_registry_filters_by_difficulty() -> None:
    datasets = DatasetRegistry().list("hard")

    assert [dataset.name for dataset in datasets] == ["hip-hop-lyrics"]


def test_registry_reports_available_names_for_unknown_dataset() -> None:
    with pytest.raises(KeyError, match="Available datasets: avengers"):
        DatasetRegistry().get("missing")
