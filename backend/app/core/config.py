from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"

    # Neon PostgreSQL for cloud deployment; override using private DATABASE_URL.
    database_url: str = "postgresql+psycopg://localhost/vtab_sales"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        # Neon supplies a standard PostgreSQL URI; select the installed Psycopg 3 driver.
        from sqlalchemy.engine import make_url
        url = make_url(value)
        if url.drivername in {"postgres", "postgresql"}:
            url = url.set(drivername="postgresql+psycopg")
        if (url.host or "").endswith(".neon.tech"):
            query = dict(url.query)
            query["sslmode"] = "require"
            query.pop("sslrootcert", None)
            url = url.set(query=query)
        return url.render_as_string(hide_password=False)

    initialize_schema: bool = False
    scheduler_enabled: bool = True

    redis_url: str = "redis://localhost:6379/0"

    # When true, outbound email is always simulated.
    demo_mode: bool = True

    demo_auth: bool = False
    demo_otp: str = "123456"
    ai_provider: str = "local"
    ai_endpoint: str = "https://api.openai.com/v1/chat/completions"
    openai_api_key: str = ""
    openai_model: str = "gpt-5-mini"
    # Optional live global web-search provider. Without this key, configured RSS/website sources still run.
    serper_api_key: str = ""
    # Read-only company materials connectors; configure privately, never in the browser.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""
    google_drive_folder_ids: str = ""
    github_read_token: str = ""

    # Microsoft Graph application authentication.
    microsoft_tenant_id: str = ""
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_sender_email: str = ""

    graph_timeout_seconds: float = 30.0

    jwt_secret: str = ""
    login_email: str = "contactsales@vtabsquare.com"
    login_password: str = ""
    qualification_threshold: int = 65
    daily_outreach_limit: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
