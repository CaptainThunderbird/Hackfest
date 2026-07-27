"""Safe, consolidated CSV and Excel dataset ingestion."""

import csv
from io import StringIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from minidatadev.data.registry import DatasetRegistry

DataSource = str | Path | BinaryIO


class DatasetLoadError(ValueError):
    """Raised when a dataset cannot be validated or loaded."""


class DatasetLoader:
    """Load uploaded files, local paths, or registered sample datasets."""

    SUPPORTED_EXTENSIONS = frozenset({".csv", ".xls", ".xlsx"})

    def __init__(self, registry: DatasetRegistry | None = None):
        self.registry = registry or DatasetRegistry()

    def load(self, source: DataSource, *, filename: str | None = None) -> pd.DataFrame:
        """Load a CSV or Excel source and attach basic provenance metadata.

        A string matching a registry key loads that sample. Other strings and
        ``Path`` objects are treated as file paths. File-like uploads must include
        ``filename`` unless their object exposes a ``name`` attribute.
        """

        sample_name = source if isinstance(source, str) else None
        if sample_name and sample_name in self.registry.names():
            metadata = self.registry.get(sample_name)
            frame = self._read_csv(str(metadata.url))
            frame.attrs.update(
                {
                    "source_type": "sample",
                    "source_name": metadata.name,
                    "description": metadata.description,
                    "difficulty": metadata.difficulty,
                    "key_columns": list(metadata.key_columns),
                }
            )
            return frame

        resolved_name = filename or getattr(source, "name", None)
        if isinstance(source, (str, Path)):
            resolved_name = str(source)
        if not resolved_name:
            raise DatasetLoadError(
                "A filename is required for uploaded data so its format can "
                "be validated."
            )

        extension = Path(resolved_name).suffix.lower()
        if extension not in self.SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(self.SUPPORTED_EXTENSIONS))
            raise DatasetLoadError(
                f"Unsupported file type '{extension or 'unknown'}'. "
                f"Supported types: {supported}"
            )

        try:
            frame = (
                self._read_csv(source)
                if extension == ".csv"
                else pd.read_excel(source)
            )
        except (OSError, ValueError, UnicodeError, pd.errors.ParserError) as error:
            raise DatasetLoadError(
                f"Could not load '{Path(resolved_name).name}': {error}"
            ) from error

        if frame.columns.empty:
            raise DatasetLoadError("The dataset does not contain any columns.")
        frame.attrs.update(
            {
                "source_type": "upload",
                "source_name": Path(resolved_name).name,
            }
        )
        return frame

    def list_datasets(self) -> dict[str, str]:
        """Return sample dataset names and descriptions."""

        return {item.name: item.description for item in self.registry.list()}

    def get_datasets_by_difficulty(self, level: str) -> list[str]:
        """Compatibility helper for existing notebooks."""

        return [item.name for item in self.registry.list(level)]

    @staticmethod
    def _read_csv(source: DataSource) -> pd.DataFrame:
        _validate_csv_shape(source)
        try:
            return pd.read_csv(source, encoding="utf-8", on_bad_lines="error")
        except UnicodeDecodeError:
            if hasattr(source, "seek"):
                source.seek(0)
            return pd.read_csv(source, encoding="latin-1", on_bad_lines="error")


def _validate_csv_shape(source: DataSource) -> None:
    """Reject inconsistent field counts before Pandas can infer an index."""

    if isinstance(source, str) and source.startswith(("http://", "https://")):
        return
    raw: bytes | None = None
    if hasattr(source, "read"):
        source.seek(0)
        raw = source.read()
        source.seek(0)
        if isinstance(raw, str):
            raw = raw.encode()
    elif isinstance(source, (str, Path)):
        raw = Path(source).read_bytes()
    if raw is None:
        return
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    rows = [
        row
        for row in csv.reader(StringIO(text))
        if row and any(value.strip() for value in row)
    ]
    if not rows:
        return
    expected = len(rows[0])
    invalid = [
        index
        for index, row in enumerate(rows[1:], start=2)
        if len(row) != expected
    ]
    if invalid:
        locations = ", ".join(str(index) for index in invalid[:5])
        raise DatasetLoadError(
            f"CSV rows have inconsistent field counts at line(s): {locations}."
        )
