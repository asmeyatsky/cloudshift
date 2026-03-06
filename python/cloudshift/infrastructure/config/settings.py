"""Application settings backed by pydantic-settings."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """CloudShift configuration.

    Values are loaded in order of precedence:
        1. Explicit constructor kwargs
        2. Environment variables (prefix ``CLOUDSHIFT_``)
        3. ``.env`` file in the working directory
    """

    model_config = SettingsConfigDict(
        env_prefix="CLOUDSHIFT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- Project defaults --
    project_name: str = Field(default="cloudshift", description="Default project name.")
    db_path: Path = Field(default=Path("cloudshift.db"), description="SQLite database path.")
    patterns_dir: Path = Field(default=Path("patterns"), description="Directory containing YAML pattern files.")

    # -- LLM --
    llm_enabled: bool = Field(default=False, description="Enable LLM-assisted transformations.")
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama API base URL.")
    ollama_model: str = Field(default="codellama:13b", description="Ollama model name.")
    ollama_timeout: float = Field(default=120.0, description="Ollama request timeout in seconds.")

    # -- Validation --
    test_timeout: int = Field(default=300, description="Test runner timeout in seconds.")
    max_residual_refs: int = Field(default=0, description="Max allowed residual cloud references.")

    # -- Logging / debug --
    log_level: str = Field(default="INFO", description="Logging level.")
    debug: bool = Field(default=False, description="Enable debug mode.")
