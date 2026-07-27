class DatasetAssistant:
    def __init__(self, loader):
        self.loader = loader  # DatasetLoader instance
        self.projects = {
            "avengers": {
                "task": "Count characters who died more than once",
                "solution": "df[df['Deaths'] > 1]",
                "hint": "Filter the 'Deaths' column for values > 1"
            },
            "college-majors": {
                "task": "Find the top 5 highest-paying majors",
                "solution": "df.sort_values('Median', ascending=False).head(5)",
                "hint": "Sort by 'Median' column"
            }
        }

    def respond(self, query: str) -> dict:
        """Process user queries and return project instructions"""
        query = query.lower()
        
        # Check for dataset mentions
        for dataset in self.projects:
            if dataset in query:
                df = self.loader.load(dataset)
                return {
                    "dataset": dataset,
                    "task": self.projects[dataset]["task"],
                    "hint": self.projects[dataset]["hint"],
                    "columns": list(df.columns)  # Show available columns
                }
        
        # Default response
        return {
            "error": "Dataset not recognized",
            "available_datasets": list(self.projects.keys())
        }
