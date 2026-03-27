from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://localhost:5432/memory_autopilot"
    elevenlabs_webhook_secret: str = ""
    elevenlabs_agent_id: str = ""
    allowed_origins: str = "http://localhost:3000"
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-sonnet-4-6"
    log_level: str = "INFO"

    model_config = {"env_file": ".env"}


settings = Settings()
