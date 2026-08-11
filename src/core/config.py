from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Sandbox limits
    SANDBOX_IMAGE: str = "python:3.11-slim"
    SANDBOX_MEM_LIMIT: str = "512m"
    SANDBOX_CPU_QUOTA: int = 100000
    EXECUTION_TIMEOUT_SECONDS: int = 220
    MAX_ITERATIONS: int = 10
    
    # Custom LLM Settings
    LLM_BASE_URL: str = "https://joke-abilities-assistant-ticket.trycloudflare.com/v1"
    LLM_MODEL: str = "qwen3-coder-next:latest"  # Company's coding model
    LLM_TEMPERATURE: float = 0.0
    OPENAI_API_KEY: str = "sk-no-key-required"  # Dummy key to satisfy the SDK

    class Config:
        env_file = ".env"

settings = Settings()