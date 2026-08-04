"""Packaged project, export, privacy, and diagnostics page."""

import streamlit as st

from minidatadev.analysis import profile_dataframe
from minidatadev.config import get_settings
from minidatadev.projects.exports import export_csv, export_report
from minidatadev.projects.monitoring import health_snapshot
from minidatadev.projects.sessions import set_active_dataset
from minidatadev.projects.storage import ProjectStore


def render() -> None:
    settings = get_settings()
    store = ProjectStore(settings.database_path, settings.data_dir)
    st.markdown('<div class="mdd-eyebrow">Beta workspace</div>', unsafe_allow_html=True)
    st.markdown(
        '<h1 class="mdd-title">Keep, share, and control your work.</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="mdd-subtitle">Save projects on this device, reopen '
        "conversations, export analysis, and manage retention.</p>",
        unsafe_allow_html=True,
    )
    projects, exports, privacy = st.tabs(["Projects", "Export", "Privacy & health"])
    with projects:
        _projects(store)
    with exports:
        _exports()
    with privacy:
        _privacy(store, settings)


def _projects(store: ProjectStore) -> None:
    owner = st.text_input("Profile name", value=st.session_state.owner_name)
    st.session_state.owner_name = owner.strip() or "Local user"
    if st.session_state.active_dataset is not None:
        project_name = st.text_input(
            "Project name", value=st.session_state.active_dataset_name
        )
        if st.button("Save current project", type="primary"):
            st.session_state.active_project_id = store.save_project(
                owner=st.session_state.owner_name,
                name=project_name,
                dataset_name=st.session_state.active_dataset_name,
                frame=st.session_state.active_dataset,
                messages=st.session_state.chat_messages,
                project_id=st.session_state.active_project_id,
            )
            st.success("Project and conversation saved on this device.")
    else:
        st.info("Load a dataset before creating a project.")

    st.markdown("#### Saved projects")
    records = store.list_projects(st.session_state.owner_name)
    if not records:
        st.caption("No saved projects for this profile.")
    for record in records:
        with st.container(border=True):
            info, load, remove = st.columns([5, 1, 1])
            info.markdown(f"**{record.name}**")
            info.caption(f"{record.dataset_name} · updated {record.updated_at[:10]}")
            if load.button("Open", key=f"open_{record.id}"):
                loaded, frame, messages = store.load_project(record.id)
                set_active_dataset(
                    st.session_state,
                    frame=frame,
                    name=loaded.dataset_name,
                    profile=profile_dataframe(frame),
                )
                st.session_state.chat_messages = messages
                st.session_state.active_project_id = record.id
                st.rerun()
            if remove.button("Delete", key=f"delete_{record.id}"):
                store.delete_project(record.id)
                st.rerun()


def _exports() -> None:
    if st.session_state.active_dataset is None:
        st.info("Load a dataset to enable exports.")
        return
    safe_name = "".join(
        char if char.isalnum() or char in "-_" else "-"
        for char in st.session_state.active_dataset_name
    ).strip("-") or "dataset"
    left, right = st.columns(2)
    left.download_button(
        "Download cleaned data",
        export_csv(st.session_state.active_dataset),
        file_name=f"{safe_name}-cleaned.csv",
        mime="text/csv",
        width="stretch",
    )
    right.download_button(
        "Download analysis package",
        export_report(
            dataset_name=st.session_state.active_dataset_name,
            frame=st.session_state.active_dataset,
            messages=st.session_state.chat_messages,
            insights=st.session_state.saved_insights,
            cleaning_history=st.session_state.cleaning_history,
        ),
        file_name=f"{safe_name}-analysis.zip",
        mime="application/zip",
        width="stretch",
    )
    st.caption("Includes cleaned data, a readable report, and a manifest.")


def _privacy(store: ProjectStore, settings) -> None:
    st.markdown(
        "Projects stay in local application storage. Data is sent to an AI "
        "provider only when that provider is selected; Demo mode stays offline."
    )
    st.caption(
        f"Retention: {settings.retention_days} days · "
        f"assistant limit: {settings.requests_per_hour} requests/hour"
    )
    if st.button("Remove projects past retention period"):
        count = store.purge_older_than(settings.retention_days)
        st.success(f"Removed {count} expired project(s).")
    with st.expander("Service health"):
        st.json(health_snapshot(settings.database_path, settings.data_dir))
