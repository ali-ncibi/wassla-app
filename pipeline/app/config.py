from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "wassla-pipeline"
    database_url: str

    llm_provider: str = "mistral"
    mistral_api_key: str = ""
    mistral_base_url: str = "https://api.mistral.ai/v1"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    model_translate: str = "mistral-small-latest"
    model_categorize: str = "mistral-small-latest"
    model_summarize: str = "mistral-small-latest"
    model_evaluator: str = "mistral-medium-latest"
    model_openai: str = "gpt-4o-mini"
    llm_temperature: float = 0.2
    llm_timeout_seconds: float = 90.0
    llm_max_concurrency: int = 4

    embedding_provider: str = "mistral"
    mistral_embedding_model: str = "mistral-embed"
    embedding_dim: int = 1024
    embedding_timeout_seconds: float = 60.0

    languages: str = "en,fr,ar"
    categories: str = "world,politics,business,technology,science,health,sports,culture,environment"
    ingest_max_items: int = 50
    ingest_token: str = ""
    eval_min_score: float = 6.0
    max_body_chars: int = 12000
    rss_timeout_seconds: float = 30.0
    rss_user_agent: str = "WasslaNewsBot/1.0"
    max_feed_bytes: int = 5_000_000
    max_feed_redirects: int = 3

    rag_top_k: int = 5
    rag_min_score: float = 0.35
    rag_answer_enabled: bool = True

    cors_origins: str = "http://localhost:3000"

    phoenix_collector_endpoint: str = "http://phoenix:6006/v1/traces"
    phoenix_project_name: str = "wassla-pipeline"

    @property
    def language_list(self) -> list[str]:
        return [x.strip() for x in self.languages.split(",") if x.strip()]

    @property
    def category_list(self) -> list[str]:
        return [x.strip() for x in self.categories.split(",") if x.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
