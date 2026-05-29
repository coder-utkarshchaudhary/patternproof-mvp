from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
ROOT_DIR = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PP_", env_file=ROOT_DIR / ".env", extra="ignore")

    # ── Application ──────────────────────────────────────────────────────
    app_name: str = "Pattern Proof"
    debug: bool = False
    frontend_origin: str = "http://localhost:3000"

    # ── Queue (Celery / Redis) ───────────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"

    # ── Supabase (Postgres relational + JSONB document store + Storage) ──
    supabase_url: str
    supabase_service_key: str
    # Storage bucket names
    bucket_screenshots: str = "screenshots"
    bucket_html: str = "html"
    bucket_reports: str = "reports"

    # ── LLM providers (hybrid) ───────────────────────────────────────────
    # Claude — manager + slave agent reasoning and vision explanations
    anthropic_api_key: str
    claude_agent_model: str = "claude-sonnet-4-6"
    claude_vision_model: str = "claude-sonnet-4-6"
    # OpenAI — cheap, high-volume per-page HTML semantic parsing
    ollama_base_url: str = "https://ollama.com"
    ollama_api_key: str
    cheap_parse_model: str = "gemma4:31b-cloud"

    # ── ML inference server (YOLO) ───────────────────────────────────────
    ml_inference_url: str = "http://ml-inference:8001"

    # ── Apify (crawler) ──────────────────────────────────────────────────
    apify_token: str
    apify_actor: str = "apify/website-content-crawler"

    # ── Exa (web search for report references) ───────────────────────────
    exa_api_key: str

    # ── Notifications (one-way) ──────────────────────────────────────────
    slack_bot_token: str
    slack_channel: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_whatsapp_from: str
    notify_whatsapp_to: str

    # ── Crawling limits ──────────────────────────────────────────────────
    crawl_max_depth: int = 3
    crawl_max_pages: int = 20
    crawl_timeout_ms: int = 30000

    # ── Agent control ────────────────────────────────────────────────────
    agent_max_iterations: int = 50
    agent_max_feedback_retries: int = 2
    low_confidence_threshold: float = 0.4

    # ── Public base URL (for building report links in notifications) ─────
    public_base_url: str = "http://localhost:8000"

    # ── Dev / testing ────────────────────────────────────────────────────
    # When True, pipeline runs immediately in a background thread instead of
    # being dispatched to the Celery broker. No Redis or worker process needed.
    eager_execution: bool = False


settings = Settings()
# print(ROOT_DIR)
# print((ROOT_DIR / ".env").exists())
# print(settings.model_dump())