"""Provider-neutral streaming clients."""

from collections.abc import Iterable, Iterator
from typing import Protocol

from minidatadev.ai.models import ChatMessage, Usage


class ChatProvider(Protocol):
    """Minimal interface implemented by every model provider."""

    name: str

    def stream(
        self,
        *,
        messages: list[ChatMessage],
        system_prompt: str,
        dataset_context: str,
    ) -> Iterator[str]:
        """Yield assistant response fragments."""

    @property
    def last_usage(self) -> Usage:
        """Return usage from the most recent request."""


class DemoProvider:
    """Offline assistant for schema exploration and product demonstrations."""

    name = "Demo"

    def __init__(self) -> None:
        self._last_usage = Usage()

    @property
    def last_usage(self) -> Usage:
        return self._last_usage

    def stream(
        self,
        *,
        messages: list[ChatMessage],
        system_prompt: str,
        dataset_context: str,
    ) -> Iterator[str]:
        del system_prompt
        import json

        context = json.loads(dataset_context)
        question = messages[-1].content.lower()
        columns = context["columns"]
        self._last_usage = Usage(requests=1)

        if any(term in question for term in ("column", "field", "schema")):
            answer = _column_answer(columns)
        elif any(term in question for term in ("missing", "null", "complete")):
            answer = _missing_answer(context, columns)
        elif any(term in question for term in ("row", "size", "shape", "record")):
            shape = context["shape"]
            answer = (
                f"**{context['dataset']}** contains **{shape['rows']:,} rows** and "
                f"**{shape['columns']:,} columns**. "
                f"I found {context['quality']['duplicate_rows']:,} duplicate rows."
            )
        elif any(term in question for term in ("question", "explore", "start")):
            answer = _suggestions(columns)
        else:
            answer = (
                "I can currently explain the dataset structure, column types, sample "
                "values, and missing data. Verified calculations such as grouped "
                "totals and period comparisons arrive with the controlled analysis "
                "tools in Phase 3. Try asking **Which columns are available?**"
            )
        yield from _chunk(answer)


class OpenAIProvider:
    """OpenAI Responses API adapter with streamed text and token accounting."""

    name = "OpenAI"

    def __init__(self, *, api_key: str, model: str) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self._last_usage = Usage()

    @property
    def last_usage(self) -> Usage:
        return self._last_usage

    def stream(
        self,
        *,
        messages: list[ChatMessage],
        system_prompt: str,
        dataset_context: str,
    ) -> Iterator[str]:
        self._last_usage = Usage(requests=1)
        input_messages = [
            {"role": item.role, "content": item.content} for item in messages
        ]
        input_messages.insert(
            0,
            {
                "role": "developer",
                "content": f"ACTIVE DATASET CONTEXT:\n{dataset_context}",
            },
        )
        stream = self.client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=input_messages,
            stream=True,
        )
        for event in stream:
            event_type = getattr(event, "type", "")
            if event_type == "response.output_text.delta":
                yield getattr(event, "delta", "")
            elif event_type == "response.completed":
                usage = getattr(getattr(event, "response", None), "usage", None)
                self._last_usage = Usage(
                    input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
                    output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
                    requests=1,
                )


def _column_answer(columns: list[dict]) -> str:
    rendered = "\n".join(
        f"- **{item['name']}** — {item['semantic_type']}"
        for item in columns[:20]
    )
    suffix = (
        f"\n\n…and {len(columns) - 20} more columns."
        if len(columns) > 20
        else ""
    )
    return f"The dataset has {len(columns)} columns:\n\n{rendered}{suffix}"


def _missing_answer(context: dict, columns: list[dict]) -> str:
    affected = sorted(
        (item for item in columns if item["missing"]),
        key=lambda item: item["missing"],
        reverse=True,
    )
    if not affected:
        return (
            f"The dataset is **100% complete** across "
            f"{context['shape']['rows']:,} rows."
        )
    rendered = "\n".join(
        f"- **{item['name']}**: {item['missing']:,} missing"
        for item in affected[:8]
    )
    return (
        f"Overall completeness is **{context['quality']['completeness_percent']}%**. "
        f"The main gaps are:\n\n{rendered}"
    )


def _suggestions(columns: list[dict]) -> str:
    numeric = [item["name"] for item in columns if item["semantic_type"] == "number"]
    categorical = [
        item["name"] for item in columns if item["semantic_type"] == "category"
    ]
    suggestions = [
        "Which columns have missing values?",
        "Explain the dataset structure.",
    ]
    if numeric:
        suggestions.append(f"What does the `{numeric[0]}` column contain?")
    if categorical:
        suggestions.append(f"What values appear in `{categorical[0]}`?")
    return "Good starting questions:\n\n" + "\n".join(
        f"- {item}" for item in suggestions
    )


def _chunk(text: str, size: int = 24) -> Iterable[str]:
    words = text.split(" ")
    for index in range(0, len(words), size):
        suffix = " " if index + size < len(words) else ""
        yield " ".join(words[index : index + size]) + suffix
