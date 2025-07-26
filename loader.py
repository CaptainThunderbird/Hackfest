import pandas as pd
from typing import Dict, Optional, List

class DatasetLoader:
    def __init__(self):
        self.datasets = {
            # MARVEL/AVENGERS
            "avengers": {
                "url": "https://raw.githubusercontent.com/fivethirtyeight/data/master/avengers/avengers.csv",
                "difficulty": "easy",
                "key_columns": ["Name", "Death1", "Gender", "Year"],
                "quick_tasks": [
                    "df[df['Gender'] == 'Female'].shape[0]  # Count female characters",
                    "df.groupby('Year')['Death1'].sum().plot()  # Deaths by year"
                ]
            },
            
            # MAJORS
            "majors": {
                "url": "https://raw.githubusercontent.com/fivethirtyeight/data/master/college-majors/majors-list.csv",
                "difficulty": "medium",
                "key_columns": ["Major", "Major_category", "Total"],
                "quick_tasks": [
                    "df.nlargest(10, 'Total')  # Top 10 most popular majors",
                    "df['Major_category'].value_counts().plot.pie()  # Major categories"
                ]
            },
            
            # LYRICS
            "lyrics": {
                "url": "https://raw.githubusercontent.com/fivethirtyeight/data/master/hip-hop-candidate-lyrics/genius_hip_hop_lyrics.csv",
                "difficulty": "medium",
                "key_columns": ["artist", "album", "candidate", "sentiment"],
                "quick_tasks": [
                    "df['candidate'].value_counts().plot(kind='bar')  # Candidate mentions",
                    "df.groupby('artist')['sentiment'].mean().sort_values()  # Sentiment by artist"
                ],
                "preprocessing": """
# Clean sentiment scores
df['sentiment'] = pd.to_numeric(df['sentiment'], errors='coerce')"""
            },
            
            # MASCULINITY
            "masculinity": {
                "url": "https://raw.githubusercontent.com/fivethirtyeight/data/master/masculinity-survey/masculinity-survey.csv",
                "difficulty": "hard",
                "key_columns": ["question", "response", "count", "percentage"],
                "quick_tasks": [
                    "df[df['question'].str.contains('important')]  # Filter questions about importance",
                    "df.pivot(index='question', columns='response', values='count').plot.barh(stacked=True)  # Stacked responses"
                ],
                "preprocessing": """
# Convert percentages to float
df['percentage'] = df['percentage'].str.rstrip('%').astype('float')"""
            }
        }

    def load(self, name: str) -> Optional[pd.DataFrame]:
        try:
            if name not in self.datasets:
                raise ValueError(f"Unknown dataset: {name}")
                
            df = pd.read_csv(
                self.datasets[name]["url"],
                encoding='latin-1',
                on_bad_lines='warn'
            )
            
            # Apply preprocessing
            if "preprocessing" in self.datasets[name]:
                exec(self.datasets[name]["preprocessing"], globals(), {'df': df})
            
            # attach metadata
            df.attrs = {
                'difficulty': self.datasets[name]["difficulty"],
                'key_columns': self.datasets[name]["key_columns"],
                'quick_tasks': self.datasets[name]["quick_tasks"]
            }
            
            return df
            
        except Exception as e:
            print(f"⚠️ Error loading {name}: {str(e)}")
            return None

    # Helper methods
    def get_datasets_by_difficulty(self, level: str) -> List[str]:
        return [name for name, data in self.datasets.items() 
                if data["difficulty"] == level]

    def get_quick_task(self, dataset_name: str, index: int = 0) -> str:
        return self.datasets.get(dataset_name, {}).get("quick_tasks", [""])[index]