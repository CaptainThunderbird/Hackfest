from streamlit.testing.v1 import AppTest


def test_app_loads_local_sample_without_exceptions() -> None:
    app = AppTest.from_file("app.py", default_timeout=30).run()

    assert not app.exception
    assert [button.label for button in app.button] == ["Load sample"]

    app.button[0].click().run()

    assert not app.exception
    assert app.session_state["active_dataset_name"] == "avengers"
    assert app.success[0].value == "Dataset loaded and profiled."
