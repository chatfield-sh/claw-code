"""Configuration. Everything optional in dev — the API degrades gracefully."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql://shai:shai@localhost:5432/shai"

    # Claude. Without a key, agents + the generic module use a heuristic fallback.
    anthropic_api_key: str = ""
    shai_model: str = "claude-sonnet-4-6"

    # Secret for signing OAuth state + encrypting stored tokens at rest.
    # Override in every real environment.
    shai_secret_key: str = "dev-insecure-change-me"

    # Clerk. Without keys, the API resolves the single dev tenant/user below.
    clerk_secret_key: str = ""

    # Google connectors (optional in the scaffold).
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/google/callback"

    # Single dev tenant/user (must match db/seed.sql).
    shai_dev_tenant_id: str = "00000000-0000-0000-0000-000000000001"
    shai_dev_user_id: str = "00000000-0000-0000-0000-000000000002"

    @property
    def has_claude(self) -> bool:
        return bool(self.anthropic_api_key)


settings = Settings()
