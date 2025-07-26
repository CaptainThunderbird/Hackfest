import pandas as pd
from typing import Dict, Optional, List


# otherr preprocessing functions
def preprocess_lyrics(df: pd.DataFrame) -> None:
    df['sentiment'] = pd.to_numeric(df['sentiment'], errors='coerce')

def preprocess_masculinity(df: pd.DataFrame) -> None:
    df['percentage'] = df['percentage'].str.rstrip('%').astype('float')


class DatasetLoader:
    def __init__(self):
        self.datasets = {
            #MARVEL/AVENGERS
            "avengers": {
                "url": "https://raw.githubusercontent.com/fivethirtyeight/data/master/avengers/avengers.csv",
                "preprocessing_fn": None,
                "meta": {
                    "difficulty": "easy",
                    "description": "Marvel's Avengers character data including gender, membership year, and character deaths.",
                    "key_columns": ["Name", "Death1", "Gender", "Year"],
                    "columns_info": {
                        "Name": "Hero's name",
                        "Death1": "Whether the character died (1 = yes, 0 = no)",
                        "Gender": "Character's gender",
                        "Year": "Year the character joined the Avengers"
                    },
                    "quick_tasks": [
                        "df[df['Gender'] == 'Female'].shape[0]  # Count female characters",
                        "df.groupby('Year')['Death1'].sum().plot()  # Deaths by year"
                    ]
                }
            },

            #MAJORS
            "majors": {
                "url": "https://raw.githubusercontent.com/fivethirtyeight/data/master/college-majors/majors-list.csv",
                "preprocessing_fn": None,
                "meta": {
                    "difficulty": "medium",
                    "description": "List of college majors with their categories and number of graduates.",
                    "key_columns": ["Major", "Major_category", "Total"],
                    "columns_info": {
                        "Major": "Name of the major",
                        "Major_category": "Broader category of the major",
                        "Total": "Total number of graduates"
                    },
                    "quick_tasks": [
                        "df.nlargest(10, 'Total')  # Top 10 most popular majors",
                        "df['Major_category'].value_counts().plot.pie()  # Major categories"
                    ]
                }
            },

            #LYRICS
            "lyrics": {
                "url": "https://raw.githubusercontent.com/fivethirtyeight/data/master/hip-hop-candidate-lyrics/genius_hip_hop_lyrics.csv",
                "preprocessing_fn": preprocess_lyrics,
                "meta": {
                    "difficulty": "medium",
                    "description": "Hip-hop lyrics mentioning US presidential candidates, with sentiment scores.",
                    "key_columns": ["artist", "album", "candidate", "sentiment"],
                    "columns_info": {
                        "artist": "Name of the artist",
                        "album": "Album name",
                        "candidate": "Candidate mentioned in the lyrics",
                        "sentiment": "Sentiment score (-1 to 1)"
                    },
                    "quick_tasks": [
                        "df['candidate'].value_counts().plot(kind='bar')  # Candidate mentions",
                        "df.groupby('artist')['sentiment'].mean().sort_values()  # Sentiment by artist"
                    ]
                }
            },

            #MASCULINITY
            "masculinity": {
                "url": "https://raw.githubusercontent.com/fivethirtyeight/data/master/masculinity-survey/masculinity-survey.csv",
                "preprocessing_fn": preprocess_masculinity,
                "meta": {
                    "difficulty": "hard",
                    "description": "Survey results about masculinity and perceptions in US culture.",
                    "key_columns": ["question", "response", "count", "percentage"],
                    "columns_info": {
                        "question": "Survey question asked",
                        "response": "Response choice (e.g. Agree, Disagree)",
                        "count": "Number of respondents",
                        "percentage": "Percentage of respondents"
                    },
                    "quick_tasks": [
                        "df[df['question'].str.contains('important')]  # Questions about importance",
                        "df.pivot(index='question', columns='response', values='count').plot.barh(stacked=True)  # Stacked responses"
                    ]
                }
            }
        }

    def load(self, name: str) -> Optional[pd.DataFrame]:
        try:
            if name not in self.datasets:
                raise ValueError(f"Unknown dataset: {name}")
            
            dataset = self.datasets[name]
            df = pd.read_csv(
                dataset["url"],
                encoding='latin-1',
                on_bad_lines='warn'
            )

            # Apply preprocessing
            if dataset["preprocessing_fn"]:
                dataset["preprocessing_fn"](df)

            # Attach metadata
            df.attrs = dataset.get("meta", {})

            return df

        except Exception as e:
            print(f"⚠️ Error loading dataset '{name}': {e}")
            return None

    # Helper Methods
    def get_datasets_by_difficulty(self, level: str) -> List[str]:
        return [name for name, d in self.datasets.items() if d.get("meta", {}).get("difficulty") == level]

    def get_quick_task(self, dataset_name: str, index: int = 0) -> str:
        return self.datasets.get(dataset_name, {}).get("meta", {}).get("quick_tasks", [""])[index]

    def get_dataset_description(self, name: str) -> Optional[str]:
        return self.datasets.get(name, {}).get("meta", {}).get("description", "")

    def get_column_info(self, name: str) -> Optional[Dict[str, str]]:
        return self.datasets.get(name, {}).get("meta", {}).get("columns_info", {})

    def list_datasets(self) -> List[Dict[str, str]]:
        return [
            {
                "name": name,
                "description": data.get("meta", {}).get("description", ""),
                "difficulty": data.get("meta", {}).get("difficulty", "unknown")
            }
            for name, data in self.datasets.items()
        ]
