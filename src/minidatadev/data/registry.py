"""Registry of sample datasets available to MiniDataDev."""

from collections.abc import Iterable

from minidatadev.data.models import DatasetMetadata

DEFAULT_DATASETS = (
    DatasetMetadata(
        name="avengers",
        description="Marvel character deaths and resurrections",
        url="https://raw.githubusercontent.com/fivethirtyeight/data/master/avengers/avengers.csv",
        difficulty="easy",
        key_columns=("Name/Alias", "Gender", "Year", "Death1"),
    ),
    DatasetMetadata(
        name="college-majors",
        description="Enrollment totals grouped by college major",
        url="https://raw.githubusercontent.com/fivethirtyeight/data/master/college-majors/majors-list.csv",
        difficulty="medium",
        key_columns=("Major", "Major_category", "Total"),
    ),
    DatasetMetadata(
        name="hip-hop-lyrics",
        description="Presidential candidate mentions in hip-hop lyrics",
        url="https://raw.githubusercontent.com/fivethirtyeight/data/master/hip-hop-candidate-lyrics/genius_hip_hop_lyrics.csv",
        difficulty="hard",
        key_columns=("artist", "album", "candidate", "sentiment"),
    ),
    DatasetMetadata(
        name="masculinity-survey",
        description="Survey responses about masculinity in the United States",
        url="https://raw.githubusercontent.com/fivethirtyeight/data/master/masculinity-survey/masculinity-survey.csv",
        difficulty="medium",
        key_columns=("question", "response", "count", "percentage"),
    ),
    DatasetMetadata(
        name="bechdel",
        description="Movie gender representation and Bechdel test results",
        url="https://raw.githubusercontent.com/fivethirtyeight/data/master/bechdel/movies.csv",
        difficulty="easy",
    ),
    DatasetMetadata(
        name="candy",
        description="Halloween candy popularity rankings",
        url="https://raw.githubusercontent.com/fivethirtyeight/data/master/candy-power-ranking/candy-data.csv",
        difficulty="easy",
    ),
    DatasetMetadata(
        name="nfl-tweets",
        description="NFL team Twitter engagement metrics",
        url="https://raw.githubusercontent.com/fivethirtyeight/data/master/nfl-fandom/nfl_twitter_ratio.csv",
        difficulty="medium",
    ),
)


class DatasetRegistry:
    """Lookup service for known sample datasets."""

    def __init__(self, datasets: Iterable[DatasetMetadata] = DEFAULT_DATASETS):
        self._datasets = {dataset.name: dataset for dataset in datasets}

    def get(self, name: str) -> DatasetMetadata:
        """Return a dataset definition or raise a descriptive error."""

        try:
            return self._datasets[name]
        except KeyError as error:
            available = ", ".join(self.names())
            raise KeyError(
                f"Unknown dataset '{name}'. Available datasets: {available}"
            ) from error

    def list(self, difficulty: str | None = None) -> tuple[DatasetMetadata, ...]:
        """List datasets, optionally filtered by difficulty."""

        datasets = tuple(self._datasets.values())
        if difficulty is None:
            return datasets
        return tuple(item for item in datasets if item.difficulty == difficulty)

    def names(self) -> tuple[str, ...]:
        """Return registered dataset names in display order."""

        return tuple(self._datasets)
