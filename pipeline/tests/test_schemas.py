from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas import (
    ArticleCard,
    ArticleDetail,
    ArticlesResponse,
    ArticleSummary,
    CategoryCount,
    ConfigView,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    RagConfig,
    SearchHit,
    SearchResponse,
    StatsResponse,
    TranslationDraft,
)


def test_ingest_request_bounds() -> None:
    assert IngestRequest().max_items is None
    assert IngestRequest(max_items=1).max_items == 1
    assert IngestRequest(max_items=500).max_items == 500
    with pytest.raises(ValidationError):
        IngestRequest(max_items=0)
    with pytest.raises(ValidationError):
        IngestRequest(max_items=501)


def test_rag_config_bounds() -> None:
    assert RagConfig(top_k=1, min_score=0.0, answer_enabled=True).top_k == 1
    with pytest.raises(ValidationError):
        RagConfig(top_k=0, min_score=0.0, answer_enabled=True)
    with pytest.raises(ValidationError):
        RagConfig(top_k=51, min_score=0.0, answer_enabled=True)
    with pytest.raises(ValidationError):
        RagConfig(top_k=5, min_score=1.5, answer_enabled=True)
    with pytest.raises(ValidationError):
        RagConfig(top_k=5, min_score=-0.1, answer_enabled=True)


def test_response_models_instantiate() -> None:
    now = datetime(2026, 1, 1, 12, 0, 0)
    summary = ArticleSummary(id=1, title="t", category="world", eval_score=8.0, status="processed")
    resp = IngestResponse(
        fetched=3, duplicates_skipped=1, processed=2, failed=1, duration_ms=42, articles=[summary], errors=["e"]
    )
    assert resp.processed == 2
    card = ArticleCard(
        id=1,
        title="t",
        summary="s",
        category="world",
        source_name="src",
        url="http://x",
        published_at=now,
        scraped_at=now,
    )
    assert ArticlesResponse(total=1, items=[card]).total == 1
    detail = ArticleDetail(
        id=1,
        title="t",
        body="b",
        summary="s",
        category="world",
        lang="en",
        source_language="en",
        source_name="src",
        url="http://x",
        published_at=now,
        scraped_at=now,
        eval_score=8.0,
        eval_verdict="pass",
        available_langs=["en", "fr"],
    )
    assert detail.available_langs == ["en", "fr"]
    hit = SearchHit(
        article_id=1,
        title="t",
        summary="s",
        category="world",
        source_name="src",
        url="http://x",
        published_at=now,
        score=0.9,
    )
    assert SearchResponse(query="q", lang="en", answer="a", hits=[hit]).hits[0].score == 0.9
    counts = CategoryCount(name="world", count=3)
    stats = StatsResponse(
        total_articles=10,
        needs_review=2,
        avg_eval_score=7.5,
        last_scraped_at=now,
        by_category=[counts],
        by_language=[counts],
        per_day_target=200,
    )
    assert stats.per_day_target == 200
    cfg = ConfigView(
        llm_provider="stub",
        embedding_provider="stub",
        languages=["en"],
        categories=["world"],
        models={"translate": "stub"},
        eval_min_score=6.0,
        ingest_max_items=50,
        rag=RagConfig(top_k=5, min_score=0.35, answer_enabled=True),
    )
    assert cfg.models == {"translate": "stub"}
    health = HealthResponse(
        status="ok",
        database="ok",
        llm_provider="stub",
        llm_models={"translate": "stub"},
        embedding_provider="stub",
        embedding_dim=1024,
    )
    assert health.status == "ok"
    draft: TranslationDraft = {"title": "t", "body": "b"}
    assert draft["title"] == "t"
