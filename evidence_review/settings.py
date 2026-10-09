import os
import tomllib
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    model_id: str = "command-a-03-2025"
    temperature: float = Field(default=0, ge=0, le=1)
    max_tokens: int = Field(default=1000, ge=100, le=4000)
    thinking: Literal["disabled"] = "disabled"
    output_format: Literal["json_schema", "json_object"] = "json_object"
    default_mode: Literal["replay", "live"] = "replay"
    default_strategy: Literal["retrieval", "full_context"] = "retrieval"
    top_k: int = Field(default=3, ge=1, le=10)
    deadline_seconds: float = Field(default=30, gt=0, le=60)
    attempt_budget: int = Field(default=50, ge=1, le=100)
    attempts_per_minute: int = Field(default=10, ge=1, le=10)
    max_retries: int = Field(default=2, ge=0, le=2)
    api_key: SecretStr = Field(default=SecretStr(""), repr=False, exclude=True)

    @classmethod
    def load(cls):
        configuration = tomllib.loads((ROOT / "app-config.toml").read_text())
        load_dotenv(ROOT / ".env", override=False)
        values = configuration["model"] | configuration["runtime"] | configuration["limits"]
        values["model_id"] = values.pop("id")
        values["api_key"] = SecretStr(os.environ.get("MODEL_API_KEY", ""))
        return cls.model_validate(values)

    def public(self):
        return self.model_dump(exclude={"api_key"})
