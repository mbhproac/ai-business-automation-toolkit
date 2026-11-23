"""Workflow configuration schemas. All config is data; no dynamic Python execution."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Action(BaseModel):
    type: Literal["record", "http_post", "ai_summarize"]
    name: str = Field(min_length=1, max_length=80)
    message: str | None = None
    url: str | None = None
    prompt: str | None = None

    @model_validator(mode="after")
    def check_action(self) -> "Action":
        if self.type == "http_post" and not self.url:
            raise ValueError("http_post requires url")
        if self.type == "ai_summarize" and not self.prompt:
            raise ValueError("ai_summarize requires prompt")
        return self


class Workflow(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    description: str = ""
    enabled: bool = True
    actions: list[Action] = Field(min_length=1, max_length=25)


class EventIn(BaseModel):
    data: dict[str, object] = Field(default_factory=dict)


class JobOut(BaseModel):
    id: str
    workflow_id: str
    status: str
    attempts: int
    created_at: str
    last_error: str | None = None
