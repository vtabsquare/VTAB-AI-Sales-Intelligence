from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"

    # Windows-native default. Override DATABASE_URL in backend/.env.
    database_url: str = (
        "mssql+pyodbc://@localhost/VTABOpportunityAgent"
        "?driver=ODBC+Driver+18+for+SQL+Server"
        "&trusted_connection=yes"
        "&TrustServerCertificate=yes"
    )

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
    openai_model: str = "gpt-5.6"
    # Optional live global web-search provider. Without this key, configured RSS/website sources still run.
    serper_api_key: str = ""

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
