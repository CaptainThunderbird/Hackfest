import pandas as pd

from minidatadev.analysis import (
    generate_insights,
    profile_dataframe,
    suggest_questions,
)


def test_generates_quality_distribution_and_relationship_insights() -> None:
    frame = pd.DataFrame(
        {
            "segment": ["A", "A", "B", "B", "B", "B", "B", "B"],
            "sales": [1, 1, 2, 2, 3, 3, 4, 100],
            "units": [2, 2, 4, 4, 6, 6, 8, 200],
            "missing": [None, None, None, "x", None, None, None, None],
        }
    )

    insights = generate_insights(frame, profile_dataframe(frame))
    titles = [item.title for item in insights]

    assert any("Missing values concentrate" in title for title in titles)
    assert any("strongly right-skewed" in title for title in titles)
    assert any("move together" in title for title in titles)
    assert all(item.evidence for item in insights)


def test_generates_complete_dataset_observation() -> None:
    frame = pd.DataFrame({"category": ["A", "B"], "value": [1, 2]})

    insights = generate_insights(frame, profile_dataframe(frame))

    assert insights[0].title == "No missing values detected"
    assert insights[0].level == "info"


def test_suggested_questions_use_real_column_names() -> None:
    frame = pd.DataFrame(
        {
            "region": ["North", "South"],
            "revenue": [10, 20],
            "profit": [2, 4],
        }
    )

    questions = suggest_questions(profile_dataframe(frame))

    assert "Describe the revenue column" in questions
    assert "Show total revenue by region" in questions
    assert "Calculate correlation between revenue and profit" in questions
