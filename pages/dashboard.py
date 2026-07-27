"""Automatic insights and editable visualization dashboard."""

import hashlib

import plotly.express as px
import streamlit as st

from minidatadev.analysis import (
    build_chart,
    generate_insights,
    profile_table,
    recommend_charts,
    suggest_questions,
)
from minidatadev.analysis.operations import AnalysisValidationError
from minidatadev.projects import save_insight


def render() -> None:
    st.markdown(
        '<div class="mdd-eyebrow">Analysis dashboard</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<h1 class="mdd-title">Patterns worth a closer look.</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="mdd-subtitle">Automatic observations, recommended charts, '
        "and an editable studio—all calculated from the active dataset.</p>",
        unsafe_allow_html=True,
    )

    if st.session_state.active_dataset is None:
        st.info("Load a dataset in **Data workspace** to populate this dashboard.")
        return

    overview, visualizations, saved = st.tabs(
        ["Automatic insights", "Chart studio", "Saved insights"]
    )
    with overview:
        _overview()
    with visualizations:
        _chart_studio()
    with saved:
        _saved_insights()


def _overview() -> None:
    frame = st.session_state.active_dataset
    profile = st.session_state.dataset_profile
    row_col, column_col, missing_col, saved_col = st.columns(4)
    row_col.metric("Rows", f"{profile.rows:,}")
    column_col.metric("Columns", f"{profile.columns:,}")
    missing_col.metric("Complete", f"{profile.completeness_percent}%")
    saved_col.metric("Saved insights", len(st.session_state.saved_insights))

    st.markdown("#### What MiniDataDev noticed")
    insights = generate_insights(frame, profile)
    if not insights:
        st.info("No notable automatic observations were detected.")
    for index in range(0, len(insights), 2):
        columns = st.columns(2)
        for offset, insight in enumerate(insights[index : index + 2]):
            with columns[offset]:
                badge = {
                    "warning": "Needs attention",
                    "opportunity": "Worth exploring",
                    "info": "Good to know",
                }[insight.level]
                st.markdown(
                    '<div class="mdd-card">'
                    f'<span class="mdd-card-label">{badge}</span>'
                    f'<div class="mdd-card-value" style="font-size:1.1rem;'
                    f'margin:.35rem 0">{insight.title}</div>'
                    f'<div style="color:#68787b">{insight.detail}</div>'
                    f'<div style="font-size:.78rem;margin-top:.65rem">'
                    f'{insight.evidence}</div></div>',
                    unsafe_allow_html=True,
                )
                if st.button(
                    "Save insight",
                    key=f"save_auto_{insight.id}",
                    width="stretch",
                ):
                    added = save_insight(
                        st.session_state,
                        {
                            **insight.model_dump(mode="json"),
                            "saved_type": "observation",
                        },
                    )
                    st.toast("Insight saved." if added else "Already saved.")

    st.markdown("#### Suggested questions")
    for question in suggest_questions(profile):
        st.markdown(f"- {question}")

    with st.expander("Data quality and schema"):
        _quality_details()


def _quality_details() -> None:
    profile = st.session_state.dataset_profile
    table = profile_table(profile)
    left, right = st.columns([1.35, 1])
    with left:
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
                height=max(300, 32 * len(missing)),
                margin=dict(l=0, r=10, t=20, b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(figure, width="stretch")
    with right:
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
            height=320,
            margin=dict(l=0, r=0, t=20, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=-0.05),
        )
        st.plotly_chart(figure, width="stretch")
    st.dataframe(table, width="stretch", hide_index=True)


def _chart_studio() -> None:
    frame = st.session_state.active_dataset
    profile = st.session_state.dataset_profile
    recommendations = recommend_charts(profile)
    if not recommendations:
        st.info("This dataset needs at least one chartable column.")
        return

    selected = st.selectbox(
        "Recommended starting point",
        recommendations,
        format_func=lambda item: f"{item.title} — {item.reason}",
    )
    st.caption(selected.reason)
    all_columns = [str(column) for column in frame.columns]
    optional_columns = ["None", *all_columns]
    chart_types = ["bar", "line", "scatter", "histogram", "box"]
    aggregations = ["none", "sum", "mean", "median", "count"]

    with st.form(f"chart_settings_{selected.id}"):
        st.markdown("#### Edit chart settings")
        first, second, third = st.columns(3)
        chart_type = first.selectbox(
            "Chart type",
            chart_types,
            index=chart_types.index(selected.chart_type),
        )
        x = second.selectbox(
            "X axis",
            all_columns,
            index=all_columns.index(selected.x),
        )
        default_y = selected.y if selected.y else "None"
        y_choice = third.selectbox(
            "Y axis",
            optional_columns,
            index=optional_columns.index(default_y),
        )
        fourth, fifth = st.columns(2)
        default_group = selected.grouping if selected.grouping else "None"
        grouping_choice = fourth.selectbox(
            "Color / grouping",
            optional_columns,
            index=optional_columns.index(default_group),
        )
        aggregation = fifth.selectbox(
            "Aggregation",
            aggregations,
            index=aggregations.index(selected.aggregation),
        )
        title = st.text_input("Chart title", value=selected.title)
        apply_settings = st.form_submit_button(
            "Update chart",
            type="primary",
            width="stretch",
        )

    signature = {
        "recommendation_id": selected.id,
        "chart_type": chart_type,
        "x": x,
        "y": None if y_choice == "None" else y_choice,
        "grouping": None if grouping_choice == "None" else grouping_choice,
        "aggregation": aggregation,
        "title": title,
    }
    if (
        apply_settings
        or st.session_state.get("chart_signature") != signature
        or st.session_state.get("active_chart") is None
    ):
        try:
            figure, chart_frame, context = build_chart(
                frame,
                chart_type=chart_type,
                x=x,
                y=signature["y"],
                grouping=signature["grouping"],
                aggregation=aggregation,
                title=title,
            )
            st.session_state.active_chart = figure
            st.session_state.active_chart_data = chart_frame
            st.session_state.active_chart_context = context
            st.session_state.chart_signature = signature
        except AnalysisValidationError as error:
            st.error(str(error))

    figure = st.session_state.get("active_chart")
    context = st.session_state.get("active_chart_context")
    if figure is not None and context is not None:
        st.plotly_chart(figure, width="stretch")
        st.caption(
            "This chart is now available to Chat. Open **Ask Mini** and say "
            "**Explain this chart**."
        )
        save_col, context_col = st.columns([1, 2])
        if save_col.button("Save chart insight", type="primary", width="stretch"):
            identifier = hashlib.sha1(
                repr(context).encode(),
                usedforsecurity=False,
            ).hexdigest()[:12]
            added = save_insight(
                st.session_state,
                {
                    "id": identifier,
                    "saved_type": "chart",
                    "title": context["title"],
                    "detail": (
                        f"{context['chart_type'].title()} chart using "
                        f"{context['x']}"
                    ),
                    "evidence": f"{context['points']:,} plotted rows",
                    "context": context,
                    "figure": figure,
                },
            )
            st.toast("Chart insight saved." if added else "Already saved.")
        context_col.info(
            "Chart context contains only plotted fields and a bounded preview."
        )


def _saved_insights() -> None:
    saved = st.session_state.saved_insights
    if not saved:
        st.info(
            "Save an automatic observation or chart to build your "
            "insight collection."
        )
        return
    st.caption(f"{len(saved)} saved items for {st.session_state.active_dataset_name}")
    for item in saved:
        with st.container(border=True):
            title_col, action_col = st.columns([5, 1])
            title_col.markdown(f"#### {item['title']}")
            title_col.write(item.get("detail", ""))
            title_col.caption(item.get("evidence", ""))
            if item.get("figure") is not None:
                st.plotly_chart(item["figure"], width="stretch")
            if action_col.button("Remove", key=f"remove_{item['id']}"):
                st.session_state.saved_insights = [
                    candidate
                    for candidate in st.session_state.saved_insights
                    if candidate["id"] != item["id"]
                ]
                st.rerun()
