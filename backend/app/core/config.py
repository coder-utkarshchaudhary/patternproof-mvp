from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "PP_"}

    # Application
    app_name: str = "Pattern Proof"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://patternproof:patternproof@localhost:5432/patternproof"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Ollama (LLM serving)
    ollama_base_url: str = "http://ollama:11434"
    agent_model: str = "mistral"
    vlm_model: str = "llava"

    # ML inference server
    ml_inference_url: str = "http://ml-inference:8001"

    # Crawling
    crawl_max_depth: int = 3
    crawl_max_pages: int = 20
    crawl_timeout_ms: int = 30000

    # Storage
    storage_dir: str = "/data/artifacts"


settings = Settings()
