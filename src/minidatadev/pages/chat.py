"""Packaged conversational dataset-exploration page."""

import streamlit as st

from minidatadev.ai import (
    ChatMessage,
    DatasetAssistant,
    DemoProvider,
    OpenAIProvider,
)
from minidatadev.analysis import explain_chart, suggest_questions
from minidatadev.analysis.operations import AnalysisValidationError
from minidatadev.config import get_settings
from minidatadev.projects.monitoring import RateLimiter, record_event


def render() -> None:
    st.markdown('<div class="mdd-eyebrow">Ask Mini</div>', unsafe_allow_html=True)
    st.markdown(
        '<h1 class="mdd-title">A conversation grounded in your data.</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="mdd-subtitle">Explore the schema, clarify definitions, and '
        "run verified calculations while inspecting exactly how each answer was "
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
    settings = get_settings()
    if st.session_state.request_limiter is None:
        st.session_state.request_limiter = RateLimiter(settings.requests_per_hour)
    if not st.session_state.request_limiter.allow():
        st.warning("Hourly assistant limit reached. Try again after it resets.")
        return
    record_event(
        settings.log_path,
        "assistant_request",
        provider=type(provider).__name__,
    )
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
        "active_chart_context": st.session_state.active_chart_context,
    }
    with st.chat_message("assistant"):
        try:
            chart_explained = False
            if (
                _is_chart_explanation(question)
                and st.session_state.active_chart_context
            ):
                chart_explained = True
                result = None
                answer = explain_chart(st.session_state.active_chart_context)
                artifact = {
                    "tool_name": "explain_chart",
                    "table": None,
                    "chart": st.session_state.active_chart,
                    "provenance": [
                        "Used the active chart configuration.",
                        "Read only calculated chart context and plotted values.",
                        "Generated no claims beyond the bounded chart context.",
                    ],
                    "assumptions": [],
                    "parameters": st.session_state.active_chart_context,
                }
                st.markdown(answer)
                _render_artifact(artifact)
            else:
                result = assistant.analyze(
                    frame=st.session_state.active_dataset,
                    question=question,
                )
            if chart_explained:
                pass
            elif result is not None:
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
    suggestions = list(suggest_questions(profile, limit=4))
    if st.session_state.active_chart_context:
        suggestions.insert(0, "Explain this chart")
    return suggestions[:4]


def _is_chart_explanation(question: str) -> bool:
    normalized = question.casefold()
    return "explain" in normalized and any(
        term in normalized for term in ("chart", "graph", "plot", "visual")
    )
