import json
import pandas as pd
from pathlib import Path

class DatasetLoader:
    def __init__(self, data_dir="../data/preloaded"):
        self.data_dir = Path(data_dir)
        with open("../config/datasets.json") as f:
            self.metadata = json.load(f)
    
    def load(self, name: str) -> pd.DataFrame:
        """Load dataset with metadata"""
        if name not in self.metadata:
            raise ValueError(f"Unknown dataset: {name}")
        return pd.read_csv(self.data_dir / self.metadata[name]["file"])