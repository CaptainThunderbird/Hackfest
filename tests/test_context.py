import json

import pandas as pd

from minidatadev.ai.context import build_dataset_context
from minidatadev.analysis import profile_dataframe


def test_context_is_bounded_and_includes_session_definitions() -> None:
    frame = pd.DataFrame(
        {
            "note": ["x" * 200, "second", "third", "not included"],
            "amount": [1, 2, 3, 4],
        }
    )

    context = json.loads(
        build_dataset_context(
            frame,
            profile_dataframe(frame),
            dataset_name="sales.csv",
            session_context={"definitions": {"revenue": "amount"}},
        )
    )

    assert context["dataset"] == "sales.csv"
    assert len(context["preview"]) == 3
    assert len(context["preview"][0]["note"]) == 120
    assert context["conversation_context"]["definitions"] == {"revenue": "amount"}
