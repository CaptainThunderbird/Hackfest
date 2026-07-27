"""Validated models used by the data ingestion layer."""

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class DatasetMetadata(BaseModel):
    """Metadata for a bundled sample dataset."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    url: HttpUrl
    difficulty: str = Field(pattern=r"^(easy|medium|hard)$")
    key_columns: tuple[str, ...] = ()
