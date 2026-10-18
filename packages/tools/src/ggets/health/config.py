from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    label: str


DEFAULT_CONFIG = Config(label="tools")


def map_config(value: dict[str, object]) -> Config:
    label = value.get("label")
    if not isinstance(label, str) or not label.strip():
        label = DEFAULT_CONFIG.label
    return Config(label=label)
