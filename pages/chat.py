"""Conversational dataset exploration page."""

import streamlit as st

from minidatadev.ai import (
    ChatMessage,
    DatasetAssistant,
    DemoProvider,
    OpenAIProvider,
)
from minidatadev.analysis.operations import AnalysisValidationError
from minidatadev.config import get_settings


def render() -> None:
    st.markdown('<div class="mdd-eyebrow">Ask Mini</div>', unsafe_allow_html=True)
    st.markdown(
        '<h1 class="mdd-title">A conversation grounded in your data.</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="mdd-subtitle">Explore the schema, clarify definitions, and '
        "run verified calculations, and inspect exactly how each answer was "
        "produced.</p>",
        unsafe_allow_html=True,
    )

    if st.session_state.active_dataset is None:
        st.info("Load a dataset in **Data workspace** before starting a conversation.")
        return

    provider = _provider_controls()
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            _render_artifact(message.get("artifact"))

    if not st.session_state.chat_messages:
        st.markdown("#### Try asking")
        suggestions = _suggestions()
        columns = st.columns(2)
        for index, suggestion in enumerate(suggestions):
            columns[index % 2].markdown(
                f'<div class="mdd-card"><span class="mdd-card-label">'
                f"{suggestion}</span></div>",
                unsafe_allow_html=True,
            )

    question = st.chat_input("Ask about this dataset…")
    if question:
        _answer(question, provider)


def _provider_controls():
    settings = get_settings()
    with st.sidebar:
        st.divider()
        st.caption("ASSISTANT")
        default = 1 if settings.ai_provider == "openai" else 0
        provider_name = st.selectbox("Provider", ["Demo", "OpenAI"], index=default)
        if provider_name == "OpenAI":
            configured = (
                settings.openai_api_key.get_secret_value()
                if settings.openai_api_key
                else ""
            )
            key = st.text_input(
                "OpenAI API key",
                value="",
                type="password",
                placeholder="Uses OPENAI_API_KEY when configured",
            )
            api_key = key or configured
            if not api_key:
                st.warning("Add a key here or use Demo mode.")
                return DemoProvider()
            st.caption(f"Model · {settings.ai_model}")
            provider = OpenAIProvider(api_key=api_key, model=settings.ai_model)
        else:
            st.caption("Offline · schema exploration")
            provider = DemoProvider()
        usage = st.session_state.usage
        if usage["requests"]:
            st.caption(
                f"{usage['requests']} requests · "
                f"{usage['input_tokens'] + usage['output_tokens']:,} tokens"
            )
        if st.session_state.chat_messages and st.button("Clear conversation"):
            st.session_state.chat_messages = []
            st.rerun()
        return provider


def _answer(question: str, provider) -> None:
    st.session_state.chat_messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    messages = [
        ChatMessage.model_validate(item)
        for item in st.session_state.chat_messages
    ]
    assistant = DatasetAssistant(provider)
    session_context = {
        "current_filters": st.session_state.current_filters,
        "definitions": st.session_state.definitions,
        "assumptions": st.session_state.assumptions,
    }
    with st.chat_message("assistant"):
        try:
            result = assistant.analyze(
                frame=st.session_state.active_dataset,
                question=question,
            )
            if result is not None:
                answer = result.summary
                artifact = result.artifact()
                st.markdown(answer)
                _render_artifact(artifact)
                for assumption in result.assumptions:
                    if assumption not in st.session_state.assumptions:
                        st.session_state.assumptions.append(assumption)
                if result.chart is not None:
                    st.session_state.saved_charts.append(result.chart)
            else:
                artifact = None
                answer = st.write_stream(
                    assistant.stream_reply(
                        frame=st.session_state.active_dataset,
                        profile=st.session_state.dataset_profile,
                        dataset_name=st.session_state.active_dataset_name,
                        messages=messages,
                        session_context=session_context,
                    )
                )
        except AnalysisValidationError as error:
            artifact = None
            answer = (
                "I can run that calculation, but I need a clearer valid request: "
                f"{error}"
            )
            st.warning(answer)
        except Exception as error:
            artifact = None
            answer = (
                "I couldn't complete that response. Check the provider settings "
                f"and try again. Details: {error}"
            )
            st.error(answer)

    st.session_state.chat_messages.append(
        {
            "role": "assistant",
            "content": str(answer),
            "artifact": artifact,
        }
    )
    usage = assistant.last_usage
    totals = st.session_state.usage
    totals["input_tokens"] += usage.input_tokens
    totals["output_tokens"] += usage.output_tokens
    totals["requests"] += usage.requests


def _render_artifact(artifact) -> None:
    if not artifact:
        return
    table = artifact.get("table")
    chart = artifact.get("chart")
    if table is not None:
        st.dataframe(table, width="stretch", hide_index=True)
    if chart is not None:
        st.plotly_chart(chart, width="stretch")
    with st.expander("How this answer was produced"):
        st.caption(f"Approved tool · {artifact['tool_name']}")
        for index, step in enumerate(artifact.get("provenance", []), start=1):
            st.markdown(f"{index}. {step}")
        assumptions = artifact.get("assumptions", [])
        if assumptions:
            st.markdown("**Assumptions**")
            for assumption in assumptions:
                st.markdown(f"- {assumption}")
        st.markdown("**Validated parameters**")
        st.json(artifact.get("parameters", {}))


def _suggestions() -> list[str]:
    profile = st.session_state.dataset_profile
    numeric = [
        item.name for item in profile.column_profiles if item.kind == "number"
    ]
    groups = [
        item.name
        for item in profile.column_profiles
        if item.kind in {"category", "text"}
    ]
    suggestions = [
        "Which columns are available?",
        "Where are values missing?",
    ]
    if numeric and groups:
        suggestions.extend(
            [
                f"Show total {numeric[0]} by {groups[0]}",
                f"Create a bar chart of total {numeric[0]} by {groups[0]}",
            ]
        )
    elif len(numeric) >= 2:
        suggestions.extend(
            [
                f"Calculate correlation between {numeric[0]} and {numeric[1]}",
                f"Find outliers in {numeric[0]}",
            ]
        )
    else:
        suggestions.extend(
            ["How many rows are in this dataset?", "Preview sample rows"]
        )
    return suggestions
