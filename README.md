# MiniDataDev

MiniDataDev is becoming an AI-assisted data-analysis workspace. The first full
version will let users upload CSV or Excel data, inspect automatic profiles and
charts, ask analytical questions conversationally, verify the calculations
behind each answer, and export results.

The current product includes the Streamlit workspace, schema-aware chatbot,
and Phase 3 controlled analysis tools.

## Technology

- Python 3.11+
- Streamlit
- Pandas, with DuckDB available for larger datasets
- Plotly
- Pydantic
- Local files and SQLite for initial persistence
- Pytest and Ruff for automated checks

## Local setup

1. Clone the repository and enter it:

   ```bash
   git clone https://github.com/CaptainThunderbird/MiniDataDev.git
   cd MiniDataDev
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   ```

   On macOS or Linux:

   ```bash
   source .venv/bin/activate
   ```

   On Windows PowerShell:

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

3. Install the package and development tools:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -e ".[dev]"
   ```

4. Copy `.env.example` to `.env` and adjust local settings if needed.

5. Start the app:

   ```bash
   streamlit run app.py
   ```

6. Run the checks:

   ```bash
   ruff check .
   pytest
   ```

## Package layout

```text
src/minidatadev/
├── ai/          # provider and chatbot integration (later phases)
├── analysis/    # validated calculations and charts (later phases)
├── data/        # CSV/Excel loading and sample registry
├── projects/    # projects and conversation state (later phases)
└── config.py    # environment-backed configuration
```

## Product capabilities

- Upload and validate CSV, XLS, and XLSX files
- Load bundled or public sample datasets
- Preview data and inspect row, column, duplicate, and completeness metrics
- Explore automatic type and missing-value visualizations
- Retain the active dataset and conversation context within the session
- Stream schema-grounded answers through a provider-neutral assistant
- Filter, sort, aggregate, correlate, compare periods, and find outliers
- Generate verified Plotly charts through conversation
- Inspect the approved tool, parameters, assumptions, and calculation steps
- Use the offline demo assistant without credentials
- Optionally use OpenAI through the Responses API

The single supported data-loading API is:

```python
from minidatadev.data import DatasetLoader

loader = DatasetLoader()
frame = loader.load("path/to/data.csv")
```

Uploaded file objects can be loaded with
`loader.load(upload, filename=upload.name)`. Registered sample data can be
loaded by name, for example `loader.load("avengers")`.

## Assistant configuration

The app starts in `demo` mode and requires no API key. Demo mode answers
questions about dataset shape, columns, and missing values.

To enable OpenAI, set these values in your uncommitted `.env`:

```dotenv
MINIDATADEV_AI_PROVIDER=openai
MINIDATADEV_AI_MODEL=gpt-5.6
OPENAI_API_KEY=your-local-key
```

The provider receives a bounded JSON context containing schema, profile,
three preview rows, and established conversation definitions. It does not
receive a dataframe object and cannot execute generated Python.

## Controlled analysis tools

Analytical questions are mapped to an allowlisted operation. Every operation
uses a strict Pydantic request model, validates columns and types against the
active dataframe, and returns a bounded table or chart with provenance.

Available operations:

- `filter_data`
- `sort_data`
- `group_and_aggregate`
- `calculate_correlation`
- `describe_column`
- `find_outliers`
- `compare_periods`
- `create_chart`
- `preview_rows`

Common explicit questions are planned deterministically. When OpenAI is
enabled, the model may select one of the same approved tools for less regular
phrasing. Model-proposed arguments remain untrusted and pass through the same
local validation before execution. Arbitrary Python, SQL, and shell execution
are not available.

## Secrets

Never commit API keys or provider credential files. Local `.env`,
`kaggle.json`, and Streamlit secrets are ignored.

An exposed Kaggle credential was removed during Phase 0. Repository removal
does not revoke that key: its owner must revoke or rotate it from the Kaggle
account settings.

## Roadmap

- Phase 0: repository rescue and reliable foundation — complete
- Phase 1: Streamlit product shell, upload, preview, and profiling — complete
- Phase 2: provider-neutral conversational assistant — complete
- Phase 3: controlled, validated analysis tools and provenance — complete
- Phase 4: automated visualizations and insights
- Phase 5: correctness, safety, latency, and cost evaluation
- Phase 6: persistent beta product and deployment
