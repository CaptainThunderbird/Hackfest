"""Dataset upload and preview page."""

from pathlib import Path

import streamlit as st

from minidatadev.analysis import profile_dataframe
from minidatadev.data import DatasetLoader, DatasetLoadError
from minidatadev.projects import set_active_dataset


def render() -> None:
    if not st.session_state.onboarding_complete:
        with st.expander("Welcome — three steps to your first answer", expanded=True):
            st.markdown(
                "1. Upload a CSV or Excel file (or choose the sample).\n"
                "2. Review automatic insights in **Dashboard**.\n"
                "3. Ask a question in **Ask Mini**, then save or export your work."
            )
    st.markdown('<div class="mdd-eyebrow">Data workspace</div>', unsafe_allow_html=True)
    st.markdown(
        '<h1 class="mdd-title">Start with data you can trust.</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="mdd-subtitle">Upload a CSV or Excel workbook, or explore a '
        "sample. MiniDataDev validates the file and builds a profile before "
        "analysis begins.</p>",
        unsafe_allow_html=True,
    )

    upload_tab, sample_tab = st.tabs(["Upload your data", "Try sample data"])
    with upload_tab:
        _upload_panel()
    with sample_tab:
        _sample_panel()

    if st.session_state.active_dataset is not None:
        _active_dataset()


def _upload_panel() -> None:
    uploaded = st.file_uploader(
        "Choose a CSV or Excel file",
        type=["csv", "xls", "xlsx"],
        help="Files are processed in this Streamlit session.",
    )
    if uploaded is not None and st.button(
        "Load uploaded dataset", type="primary", width="stretch"
    ):
        _load_source(uploaded, filename=uploaded.name)


def _sample_panel() -> None:
    loader = DatasetLoader()
    samples = loader.list_datasets()
    labels = {
        f"{name} — {description}": name for name, description in samples.items()
    }
    selected = st.selectbox("Sample dataset", labels)
    local_sample = Path("processed_avengers.csv")
    use_local = (
        labels[selected] == "avengers" and local_sample.exists()
    )
    if use_local:
        st.caption("This sample is bundled locally, so it works offline.")
    if st.button("Load sample", type="primary", width="stretch"):
        source = local_sample if use_local else labels[selected]
        _load_source(source, display_name=labels[selected])


def _load_source(
    source,
    *,
    filename: str | None = None,
    display_name: str | None = None,
) -> None:
    try:
        with st.spinner("Validating and profiling your dataset…"):
            frame = DatasetLoader().load(source, filename=filename)
            profile = profile_dataframe(frame)
        set_active_dataset(
            st.session_state,
            frame=frame,
            name=display_name or frame.attrs.get("source_name", filename or "Dataset"),
            profile=profile,
        )
        st.session_state.onboarding_complete = True
        st.success("Dataset loaded and profiled.")
    except DatasetLoadError as error:
        st.error(str(error))
    except Exception as error:
        st.error(f"We couldn't prepare this dataset: {error}")


def _active_dataset() -> None:
    frame = st.session_state.active_dataset
    profile = st.session_state.dataset_profile
    st.divider()
    title_col, badge_col = st.columns([4, 1])
    with title_col:
        st.subheader(st.session_state.active_dataset_name)
        st.caption("Ready for exploration and conversation")
    with badge_col:
        st.markdown(
            '<div class="mdd-status"><span class="mdd-dot"></span>Validated</div>',
            unsafe_allow_html=True,
        )

    row_col, column_col, complete_col, duplicate_col = st.columns(4)
    row_col.metric("Rows", f"{profile.rows:,}")
    column_col.metric("Columns", f"{profile.columns:,}")
    complete_col.metric("Complete", f"{profile.completeness_percent}%")
    duplicate_col.metric("Duplicates", f"{profile.duplicate_rows:,}")

    st.markdown("#### Data preview")
    preview_rows = st.slider("Preview rows", 5, 50, 10)
    st.dataframe(frame.head(preview_rows), width="stretch", hide_index=True)
    st.caption("Preview only. The complete dataframe remains active in this session.")
