"""Consumer contracts; provider updates remain internal."""

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StartInput(EmptyInput):
    url: HttpUrl


class SendInput(EmptyInput):
    chat_id: int
    text: str = Field(min_length=1, max_length=4096)


class OperationResult(BaseModel):
    status: str
    data: dict
