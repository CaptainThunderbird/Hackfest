from streamlit.testing.v1 import AppTest


def test_app_loads_local_sample_without_exceptions() -> None:
    app = AppTest.from_file("app.py", default_timeout=30).run()

    assert not app.exception
    assert [button.label for button in app.button] == ["Load sample"]

    app.button[0].click().run()

    assert not app.exception
    assert app.session_state["active_dataset_name"] == "avengers"
    assert app.success[0].value == "Dataset loaded and profiled."


def test_chat_renders_verified_table_chart_and_provenance() -> None:
    app = AppTest.from_file("app.py", default_timeout=30).run()
    app.button[0].click().run()
    app.radio[0].set_value("Ask Mini").run()

    app.chat_input[0].set_value(
        "Create a bar chart of total Appearances by Gender"
    ).run()

    assert not app.exception
    message = app.session_state["chat_messages"][-1]
    assert message["artifact"]["tool_name"] == "group_and_aggregate"
    assert message["artifact"]["chart"] is not None
    assert message["artifact"]["provenance"]


def test_dashboard_builds_recommended_chart_context() -> None:
    app = AppTest.from_file("app.py", default_timeout=30).run()
    app.button[0].click().run()
    app.radio[0].set_value("Dashboard").run()

    assert not app.exception
    assert app.session_state["active_chart"] is not None
    assert app.session_state["active_chart_context"]["title"]


def test_chat_explains_active_dashboard_chart() -> None:
    app = AppTest.from_file("app.py", default_timeout=30).run()
    app.button[0].click().run()
    app.radio[0].set_value("Dashboard").run()
    app.radio[0].set_value("Ask Mini").run()

    app.chat_input[0].set_value("Explain this chart").run()

    assert not app.exception
    message = app.session_state["chat_messages"][-1]
    assert message["artifact"]["tool_name"] == "explain_chart"
    assert "highest plotted value" in message["content"]
