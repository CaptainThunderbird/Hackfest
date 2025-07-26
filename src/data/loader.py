import pandas as pd
from typing import Dict, Optional

class DatasetLoader:
    def __init__(self):
        """Initialize with all FiveThirtyEight dataset URLs"""
        self.datasets: Dict[str, str] = {
            # Marvel character data
            "avengers": "https://raw.githubusercontent.com/fivethirtyeight/data/master/avengers/avengers.csv",
            
            # Education data
            "college-majors": "https://raw.githubusercontent.com/fivethirtyeight/data/master/college-majors/majors-list.csv",
            
            # Music/politics data
            "hip-hop-lyrics": "https://raw.githubusercontent.com/fivethirtyeight/data/master/hip-hop-candidate-lyrics/genius_hip_hop_lyrics.csv",
            
            # Social survey data
            "masculinity-survey": "https://raw.githubusercontent.com/fivethirtyeight/data/master/masculinity-survey/masculinity-survey.csv",
            
            # Additional datasets
            "bechdel": "https://raw.githubusercontent.com/fivethirtyeight/data/master/bechdel/movies.csv",
            "candy": "https://raw.githubusercontent.com/fivethirtyeight/data/master/candy-power-ranking/candy-data.csv",
            "nfl-tweets": "https://raw.githubusercontent.com/fivethirtyeight/data/master/nfl-fandom/nfl_twitter_ratio.csv"
        }
    
    def load(self, name: str) -> Optional[pd.DataFrame]:
        """
        Load a dataset by name
        Args:
            name: Dataset key (e.g. "avengers")
        Returns:
            pandas DataFrame or None if loading fails
        """
        try:
            return pd.read_csv(
                self.datasets[name],
                encoding='latin-1',  # Handles special characters
                on_bad_lines='warn'  # Skip problematic rows
            )
        except KeyError:
            print(f"Error: Unknown dataset '{name}'. Available datasets: {list(self.datasets.keys())}")
            return None
        except Exception as e:
            print(f"Error loading {name}: {str(e)}")
            return None
    
    def list_datasets(self) -> Dict[str, str]:
        """Return all available datasets and their descriptions"""
        return {
            "avengers": "Marvel character deaths and resurrections",
            "college-majors": "Salaries by college major",
            "hip-hop-lyrics": "2016 presidential candidate mentions in hip-hop",
            "masculinity-survey": "Survey on American men's views of masculinity",
            "bechdel": "Movie gender representation scores (Bechdel test)",
            "candy": "Halloween candy popularity rankings",
            "nfl-tweets": "NFL team Twitter engagement metrics"
        }