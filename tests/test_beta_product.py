import json
import zipfile
from datetime import UTC, datetime, timedelta
from io import BytesIO

import pandas as pd

from minidatadev.projects import ProjectStore, RateLimiter, export_report


def test_project_round_trip_and_delete(tmp_path):
    store = ProjectStore(tmp_path / "app.sqlite3", tmp_path / "data")
    frame = pd.DataFrame({"region": ["North"], "revenue": [12]})
    project_id = store.save_project(
        owner="Ada",
        name="Sales",
        dataset_name="sales.csv",
        frame=frame,
        messages=[{"role": "user", "content": "Show revenue"}],
    )
    assert store.list_projects("Ada")[0].id == project_id
    record, restored, messages = store.load_project(project_id)
    assert record.name == "Sales"
    pd.testing.assert_frame_equal(restored, frame)
    assert messages[0]["content"] == "Show revenue"
    store.delete_project(project_id)
    assert store.list_projects("Ada") == []


def test_report_package_contains_expected_files():
    payload = export_report(
        dataset_name="sales.csv",
        frame=pd.DataFrame({"revenue": [10, 20]}),
        messages=[],
        insights=[],
        cleaning_history=[
            {
                "actions": ["removed 1 duplicate row(s)"],
                "rows_before": 3,
                "rows_after": 2,
            }
        ],
    )
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        assert set(archive.namelist()) == {
            "analysis-report.html",
            "cleaned-data.csv",
            "manifest.json",
        }
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["rows"] == 2
        assert manifest["cleaning_history"][0]["rows_after"] == 2
        assert b"Cleaning history" in archive.read("analysis-report.html")


def test_rate_limiter_resets_after_window():
    limiter = RateLimiter(2, window_minutes=60)
    now = datetime.now(UTC)
    assert limiter.allow(now)
    assert limiter.allow(now)
    assert not limiter.allow(now)
    assert limiter.allow(now + timedelta(minutes=61))
