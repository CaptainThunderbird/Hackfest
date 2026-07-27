"""Provider-neutral chat models."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    """A message retained in the local conversation."""

    model_config = ConfigDict(frozen=True)

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ToolCall(BaseModel):
    """A provider-proposed call that still requires local validation."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    arguments: dict[str, Any]


class Usage(BaseModel):
    """Token and request counts reported by a provider."""

    input_tokens: int = 0
    output_tokens: int = 0
    requests: int = 0

    def add(self, other: "Usage") -> "Usage":
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            requests=self.requests + other.requests,
        )
