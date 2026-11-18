from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel, Field


class TranslationDraft(TypedDict):
    title: str
    body: str


class IngestRequest(BaseModel):
    max_items: int | None = Field(default=None, ge=1, le=500)


class ArticleSummary(BaseModel):
    id: int
    title: str
    category: str | None
    eval_score: float | None
    status: str


class IngestResponse(BaseModel):
    fetched: int
    duplicates_skipped: int
    processed: int
    failed: int
    duration_ms: int
    articles: list[ArticleSummary]
    errors: list[str]


class ArticleCard(BaseModel):
    id: int
    title: str
    summary: str | None
    category: str | None
    source_name: str
    url: str
    published_at: datetime | None
    scraped_at: datetime


class ArticlesResponse(BaseModel):
    total: int
    items: list[ArticleCard]


class ArticleDetail(BaseModel):
    id: int
    title: str
    body: str
    summary: str | None
    category: str | None
    lang: str
    source_language: str
    source_name: str
    url: str
    published_at: datetime | None
    scraped_at: datetime
    eval_score: float | None
    eval_verdict: str | None
    available_langs: list[str]


class CategoryCount(BaseModel):
    name: str
    count: int


class SearchHit(BaseModel):
    article_id: int
    title: str
    summary: str | None
    category: str | None
    source_name: str
    url: str
    published_at: datetime | None
    score: float


class SearchResponse(BaseModel):
    query: str
    lang: str
    answer: str | None
    hits: list[SearchHit]


class RagConfig(BaseModel):
    top_k: int = Field(ge=1, le=50)
    min_score: float = Field(ge=0.0, le=1.0)
    answer_enabled: bool


class ConfigView(BaseModel):
    llm_provider: str
    embedding_provider: str
    languages: list[str]
    categories: list[str]
    models: dict[str, str]
    eval_min_score: float
    ingest_max_items: int
    rag: RagConfig


class StatsResponse(BaseModel):
    total_articles: int
    needs_review: int
    avg_eval_score: float | None
    last_scraped_at: datetime | None
    by_category: list[CategoryCount]
    by_language: list[CategoryCount]
    per_day_target: int


class HealthResponse(BaseModel):
    status: str
    database: str
    llm_provider: str
    llm_models: dict[str, str]
    embedding_provider: str
    embedding_dim: int
