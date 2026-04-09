"""Configuration settings for the Agent Coach application."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Azure OpenAI
    azure_openai_endpoint: str = Field(
        default="",
        description="Azure OpenAI endpoint URL",
    )
    azure_openai_api_key: str = Field(
        default="",
        description="Azure OpenAI API key",
    )
    azure_openai_api_version: str = Field(
        default="2024-02-01",
        description="Azure OpenAI API version",
    )
    azure_openai_deployment_name: str = Field(
        default="gpt-4o",
        description="Azure OpenAI deployment / model name",
    )

    # Application behaviour
    max_coaching_recommendations: int = Field(
        default=5,
        description="Maximum number of coaching recommendations to generate per session",
    )
    mock_llm_responses: bool = Field(
        default=False,
        description=(
            "When True, skip real LLM calls and return deterministic mock responses. "
            "Useful for testing without Azure credentials."
        ),
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
