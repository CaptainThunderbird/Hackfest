"""MiniDataDev Streamlit application."""

import streamlit as st

from minidatadev.pages import beta, chat, dashboard, workspace
from minidatadev.projects import initialize_session

st.set_page_config(
    page_title="MiniDataDev",
    page_icon="▦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --ink: #17252a;
        --muted: #68787b;
        --paper: #f7f5ef;
        --card: #ffffff;
        --teal: #176b68;
        --mint: #d7ebe5;
        --coral: #e7775e;
        --line: #dfe7e3;
    }
    .stApp { background: var(--paper); color: var(--ink); }
    [data-testid="stSidebar"] { background: #102f32; }
    [data-testid="stSidebar"] * { color: #f8f5ed; }
    [data-testid="stSidebar"] hr { border-color: #315154; }
    .mdd-brand { padding: .6rem 0 1.25rem; }
    .mdd-mark {
        display: inline-grid; place-items: center; width: 2.3rem; height: 2.3rem;
        border-radius: .7rem; background: var(--coral); color: white;
        font-weight: 800; margin-right: .55rem;
    }
    .mdd-brand-name { font-size: 1.28rem; font-weight: 750; letter-spacing: -.02em; }
    .mdd-eyebrow {
        color: var(--teal); font-size: .76rem; font-weight: 750;
        letter-spacing: .12em; text-transform: uppercase; margin-bottom: .4rem;
    }
    .mdd-title {
        font-size: clamp(2rem, 4vw, 3.6rem); line-height: 1.02;
        letter-spacing: -.045em; font-weight: 750; max-width: 850px;
        margin: 0 0 .65rem;
    }
    .mdd-subtitle { color: var(--muted); font-size: 1.03rem; max-width: 760px; }
    .mdd-card {
        background: var(--card); border: 1px solid var(--line);
        border-radius: 1rem; padding: 1.1rem 1.2rem; min-height: 100%;
        box-shadow: 0 7px 24px rgba(23, 47, 47, .045);
    }
    .mdd-card-label { color: var(--muted); font-size: .8rem; font-weight: 650; }
    .mdd-card-value { font-size: 1.65rem; font-weight: 750; letter-spacing: -.03em; }
    .mdd-status {
        display: inline-flex; align-items: center; gap: .42rem;
        background: var(--mint); color: #155752; padding: .3rem .62rem;
        border-radius: 99px; font-size: .78rem; font-weight: 700;
    }
    .mdd-dot { width: .45rem; height: .45rem; border-radius: 50%; background: #24877e; }
    [data-testid="stMetric"] {
        background: white; border: 1px solid var(--line); border-radius: 1rem;
        padding: 1rem 1.1rem; box-shadow: 0 7px 24px rgba(23,47,47,.04);
    }
    .stButton > button, .stDownloadButton > button { border-radius: .7rem; }
    .stButton > button[kind="primary"] {
        background: var(--teal); border-color: var(--teal);
    }
    [data-testid="stChatMessage"] {
        background: rgba(255,255,255,.8); border: 1px solid var(--line);
        border-radius: 1rem; padding: .5rem .8rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

initialize_session(st.session_state)

with st.sidebar:
    st.markdown(
        '<div class="mdd-brand"><span class="mdd-mark">M</span>'
        '<span class="mdd-brand-name">MiniDataDev</span></div>',
        unsafe_allow_html=True,
    )
    page = st.radio(
        "Workspace navigation",
        ["Data workspace", "Dashboard", "Ask Mini", "Projects & export"],
        label_visibility="collapsed",
    )
    st.divider()
    if st.session_state.active_dataset is not None:
        profile = st.session_state.dataset_profile
        st.caption("ACTIVE DATASET")
        st.markdown(f"**{st.session_state.active_dataset_name}**")
        st.caption(f"{profile.rows:,} rows · {profile.columns:,} columns")
        if st.session_state.saved_insights:
            st.caption(f"{len(st.session_state.saved_insights)} saved insights")
    else:
        st.caption("Load a dataset to begin.")
    st.markdown("")
    st.caption("Local-first beta · Demo mode available")

if page == "Data workspace":
    workspace.render()
elif page == "Dashboard":
    dashboard.render()
elif page == "Ask Mini":
    chat.render()
else:
    beta.render()
