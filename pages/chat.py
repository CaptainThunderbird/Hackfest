"""Conversational dataset exploration page."""

import streamlit as st

from minidatadev.ai import (
    ChatMessage,
    DatasetAssistant,
    DemoProvider,
    OpenAIProvider,
)
from minidatadev.config import get_settings


def render() -> None:
    st.markdown('<div class="mdd-eyebrow">Ask Mini</div>', unsafe_allow_html=True)
    st.markdown(
        '<h1 class="mdd-title">A conversation grounded in your data.</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="mdd-subtitle">Explore the schema, clarify definitions, and '
        "prepare questions for verified analysis. Mini only uses the bounded "
        "dataset context shown by this workspace.</p>",
        unsafe_allow_html=True,
    )

    if st.session_state.active_dataset is None:
        st.info("Load a dataset in **Data workspace** before starting a conversation.")
        return

    provider = _provider_controls()
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if not st.session_state.chat_messages:
        st.markdown("#### Try asking")
        suggestions = [
            "Which columns are available?",
            "Where are values missing?",
            "How many rows are in this dataset?",
            "What questions should I explore first?",
        ]
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
            answer = st.write_stream(
                assistant.stream_reply(
                    frame=st.session_state.active_dataset,
                    profile=st.session_state.dataset_profile,
                    dataset_name=st.session_state.active_dataset_name,
                    messages=messages,
                    session_context=session_context,
                )
            )
        except Exception as error:
            answer = (
                "I couldn't complete that response. Check the provider settings "
                f"and try again. Details: {error}"
            )
            st.error(answer)

    st.session_state.chat_messages.append(
        {"role": "assistant", "content": str(answer)}
    )
    usage = assistant.last_usage
    totals = st.session_state.usage
    totals["input_tokens"] += usage.input_tokens
    totals["output_tokens"] += usage.output_tokens
    totals["requests"] += usage.requests
