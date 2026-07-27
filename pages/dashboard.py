"""Dataset profile dashboard."""

import plotly.express as px
import streamlit as st

from minidatadev.analysis import profile_table


def render() -> None:
    st.markdown(
        '<div class="mdd-eyebrow">Analysis dashboard</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<h1 class="mdd-title">Know the shape of the story.</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="mdd-subtitle">A fast quality scan of types, completeness, '
        "duplicates, and the columns available for analysis.</p>",
        unsafe_allow_html=True,
    )

    if st.session_state.active_dataset is None:
        st.info("Load a dataset in **Data workspace** to populate this dashboard.")
        return

    profile = st.session_state.dataset_profile
    row_col, column_col, missing_col, memory_col = st.columns(4)
    row_col.metric("Rows", f"{profile.rows:,}")
    column_col.metric("Columns", f"{profile.columns:,}")
    missing_col.metric("Missing cells", f"{profile.missing_cells:,}")
    memory_col.metric("Memory", _format_bytes(profile.memory_bytes))

    table = profile_table(profile)
    left, right = st.columns([1.35, 1])
    with left:
        st.markdown("#### Column quality")
        missing = table.loc[table["Missing"] > 0].sort_values(
            "Missing %", ascending=True
        )
        if missing.empty:
            st.success("Every column is complete.")
        else:
            figure = px.bar(
                missing,
                x="Missing %",
                y="Column",
                orientation="h",
                color_discrete_sequence=["#e7775e"],
            )
            figure.update_layout(
                height=max(320, 34 * len(missing)),
                margin=dict(l=0, r=10, t=10, b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis_title="Missing values (%)",
                yaxis_title=None,
            )
            st.plotly_chart(figure, width="stretch")
    with right:
        st.markdown("#### Column types")
        type_counts = (
            table["Type"].value_counts().rename_axis("Type").reset_index(name="Columns")
        )
        figure = px.pie(
            type_counts,
            values="Columns",
            names="Type",
            hole=0.64,
            color_discrete_sequence=["#176b68", "#e7775e", "#d2a94f", "#6b80a4"],
        )
        figure.update_layout(
            height=340,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=-0.05),
        )
        st.plotly_chart(figure, width="stretch")

    st.markdown("#### Schema and completeness")
    st.dataframe(
        table,
        width="stretch",
        hide_index=True,
        column_config={
            "Missing %": st.column_config.ProgressColumn(
                "Missing %", min_value=0, max_value=100, format="%.1f%%"
            )
        },
    )


def _format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"
