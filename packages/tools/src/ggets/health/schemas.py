from pydantic import BaseModel, ConfigDict


class CheckInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CheckOutput(BaseModel):
    status: str
    label: str


class InfoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InfoOutput(BaseModel):
    python_version: str
    operating_system: str
    architecture: str
