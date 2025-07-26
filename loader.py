import os
import json
import pandas as pd
from typing import Dict, Optional, Any

class DatasetLoader:
    def __init__(self, data_dir: str = "datasets"):
        self.data_dir = data_dir
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Any]:
        """Load metadata from metadata.json"""
        try:
            with open("metadata.json", "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading metadata: {e}")
            return {}

    def load(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Load dataset and attach metadata.
        Returns dictionary with keys: 'data' and 'metadata'
        """
        meta = self.metadata.get(name)
        if not meta:
            print(f"No metadata found for: {name}")
            return None

        file_path = os.path.join(self.data_dir, meta["file"])
        try:
            df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="warn")
            return {"data": df, "metadata": meta}
        except FileNotFoundError:
            print(f"Dataset file not found: {file_path}")
            return None

    def get_metadata(self, name: str) -> Dict[str, Any]:
        """Return metadata only for a dataset"""
        return self.metadata.get(name, {})
