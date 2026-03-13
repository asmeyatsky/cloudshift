"""Application settings backed by pydantic-settings."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


DeploymentMode = Literal["demo", "client"]
AuthMode = Literal["api_key", "searce_id", "password"]


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
    data_dir: Path = Field(default=Path("data"), description="Base directory for project data.")
    allowed_scan_paths: list[Path] = Field(
        default=[Path("."), Path("data"), Path("/tmp/cloudshift")],
        description="Base paths allowed for scanning (data = snippet dir; /tmp/cloudshift = imported git projects).",
    )

    # -- Deployment: demo (Gemini) vs client (Ollama) --
    deployment_mode: DeploymentMode = Field(
        default="client",
        description="demo = Gemini API; client = Ollama (e.g. Qwen 2).",
    )
    # -- LLM (client: Ollama) --
    llm_enabled: bool = Field(default=False, description="Enable LLM-assisted transformations (client mode).")
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama API base URL.")
    ollama_model: str = Field(default="qwen2:latest", description="Ollama model name (e.g. qwen2:latest).")
    ollama_timeout: float = Field(default=120.0, description="Ollama request timeout in seconds.")
    # -- LLM (demo: Gemini) --
    gemini_api_key: str | None = Field(default=None, description="Google Gemini API key (demo mode).")
    gemini_model: str = Field(default="gemini-2.5-flash", description="Gemini model name (e.g. gemini-2.5-flash; gemini-1.5-flash is deprecated).")
    gemini_timeout: float = Field(default=120.0, description="Gemini request timeout in seconds.")

    # -- Validation --
    test_timeout: int = Field(default=300, description="Test runner timeout in seconds.")
    max_residual_refs: int = Field(default=0, description="Max allowed residual cloud references.")
    min_confidence_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score required for a detection to be included in results.",
    )
    allowed_test_commands: list[str] = Field(
        default=["npm test", "pytest", "cargo test", "go test"],
        description="Whitelist of allowed test commands for validation to prevent RCE.",
    )

    # -- Static files (Web UI) --
    static_dir: Path = Field(default=Path("static"), description="Directory for static assets (index.html, etc.).")

    # -- API / Security --
    auth_mode: AuthMode = Field(
        default="api_key",
        description="api_key = single key; searce_id = demo (Searce ID); password = client (user/password).",
    )
    api_key: str | None = Field(default=None, description="Static API key (when auth_mode=api_key).")
    searce_id_issuer: str | None = Field(default=None, description="Searce ID OAuth issuer URL (demo).")
    searce_id_audience: str | None = Field(default=None, description="Searce ID audience (demo).")
    users_file: Path | None = Field(default=None, description="Path to JSON file of {username: password_hash} (auth_mode=password).")
    jwt_secret: str = Field(default="change-me-in-production", description="Secret for signing JWT (password auth).")
    jwt_ttl_seconds: int = Field(default=86400, description="JWT lifetime in seconds.")
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173", "vscode-webview://*"],
        description="Allowed CORS origins.",
    )

    # -- Logging / debug --
    log_level: str = Field(default="INFO", description="Logging level.")
    debug: bool = Field(default=False, description="Enable debug mode.")
