from collections.abc import Iterator
from datetime import datetime
from typing import Any, cast

import asyncpg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.main as main_mod
import app.repo as repo_mod
import app.routes.ingest as ingest_mod
import app.routes.search as search_mod
from app.graph.nodes import Deps
from app.main import create_app
from app.schemas import SearchResponse

from .conftest import FakeConn, FakePool, as_pool, make_deps, make_settings

NOW = datetime(2026, 1, 1, 12, 0, 0)


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    async def fake_create_pool(settings: Any) -> asyncpg.Pool:
        return as_pool(FakePool())

    monkeypatch.setattr(main_mod, "create_pool", fake_create_pool)
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def deps_of(app: FastAPI) -> Deps:
    return cast("Deps", app.state.deps)


def test_lifespan_builds_and_closes_deps(app: FastAPI) -> None:
    with TestClient(app):
        deps = deps_of(app)
        assert deps.pool is not None
        assert deps.settings.llm_provider == "stub"
        assert set(deps.chat) == {"translate", "categorize", "summarize", "evaluate"}
    pool = cast("FakePool", deps.pool)
    assert pool.closed is True


def test_root(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"service": "wassla-pipeline", "docs": "/docs"}


def test_health_ok(app: FastAPI, client: TestClient) -> None:
    deps_of(app).pool = as_pool(FakePool(FakeConn(lambda m, sql, args: 1)))
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["llm_provider"] == "stub"
    assert body["llm_models"] == {"translate": "stub", "categorize": "stub", "summarize": "stub", "evaluate": "stub"}
    assert body["embedding_provider"] == "stub"
    assert body["embedding_dim"] == 1024


def test_health_degraded_when_db_fails(app: FastAPI, client: TestClient) -> None:
    def boom(m: str, sql: str, args: tuple[Any, ...]):
        raise RuntimeError("connection refused")

    deps_of(app).pool = as_pool(FakePool(FakeConn(boom)))
    body = client.get("/health").json()
    assert body["status"] == "degraded"
    assert body["database"] == "error"


def test_config_view(client: TestClient) -> None:
    body = client.get("/config").json()
    assert body["llm_provider"] == "stub"
    assert body["languages"] == ["en", "fr", "ar"]
    assert len(body["categories"]) == 9
    assert body["eval_min_score"] == 6.0
    assert body["ingest_max_items"] == 50
    assert body["rag"] == {"top_k": 5, "min_score": 0.35, "answer_enabled": True}
    assert set(body["models"]) == {"translate", "categorize", "summarize", "evaluate"}


def test_stats(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_stats(pool: Any) -> dict[str, Any]:
        return {
            "total_articles": 12,
            "needs_review": 3,
            "avg_eval_score": 7.25,
            "last_scraped_at": NOW,
            "by_category": [{"name": "world", "count": 5}],
            "by_language": [{"name": "en", "count": 12}],
        }

    monkeypatch.setattr(repo_mod, "stats", fake_stats)
    body = client.get("/stats").json()
    assert body["total_articles"] == 12
    assert body["per_day_target"] == 200
    assert body["by_category"] == [{"name": "world", "count": 5}]


def card_row() -> dict[str, Any]:
    return {
        "id": 1,
        "title": "T",
        "summary": "s",
        "category": "world",
        "source_name": "BBC",
        "url": "http://x",
        "published_at": NOW,
        "scraped_at": NOW,
    }


def test_list_articles_passes_filters(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    async def fake_list(pool: Any, lang: str, category: str | None, limit: int, offset: int):
        captured.update(lang=lang, category=category, limit=limit, offset=offset)
        return 1, [card_row()]

    monkeypatch.setattr(repo_mod, "list_articles", fake_list)
    resp = client.get("/articles", params={"lang": "fr", "category": "world", "limit": 5, "offset": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["source_name"] == "BBC"
    assert captured == {"lang": "fr", "category": "world", "limit": 5, "offset": 2}

    client.get("/articles")
    assert (
        captured["lang"] == "en"
        and captured["category"] is None
        and captured["limit"] == 24
        and captured["offset"] == 0
    )


def test_list_articles_rejects_unsupported_lang(client: TestClient) -> None:
    resp = client.get("/articles", params={"lang": "de"})
    assert resp.status_code == 400
    assert "Unsupported language" in resp.json()["detail"]


def detail_row() -> dict[str, Any]:
    return {
        "id": 3,
        "title": "T",
        "body": "B",
        "summary": "s",
        "category": "world",
        "lang": "ar",
        "source_language": "en",
        "source_name": "BBC",
        "url": "http://x",
        "published_at": NOW,
        "scraped_at": NOW,
        "eval_score": 8.0,
        "eval_verdict": "pass",
        "available_langs": ["en", "ar"],
    }


def test_get_article(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get(pool: Any, article_id: int, lang: str):
        assert article_id == 3 and lang == "ar"
        return detail_row()

    monkeypatch.setattr(repo_mod, "get_article", fake_get)
    resp = client.get("/articles/3", params={"lang": "ar"})
    assert resp.status_code == 200
    assert resp.json()["available_langs"] == ["en", "ar"]


def test_get_article_not_found(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get(pool: Any, article_id: int, lang: str):
        return None

    monkeypatch.setattr(repo_mod, "get_article", fake_get)
    assert client.get("/articles/999").status_code == 404
    assert client.get("/articles/999", params={"lang": "de"}).status_code == 400


def test_list_categories(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_counts(pool: Any):
        return [{"name": "world", "count": 4}]

    monkeypatch.setattr(repo_mod, "category_counts", fake_counts)
    assert client.get("/categories").json() == [{"name": "world", "count": 4}]


def test_search(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    async def fake_rag(deps: Any, query: str, lang: str, rag: Any, top_k_override: int | None = None):
        captured.update(query=query, lang=lang, top_k_override=top_k_override, rag_top_k=rag.top_k)
        return SearchResponse(query=query, lang=lang, answer="ans", hits=[])

    monkeypatch.setattr(search_mod, "rag_search", fake_rag)
    resp = client.get("/search", params={"q": "ukraine war", "lang": "en", "top_k": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "ans"
    assert captured == {"query": "ukraine war", "lang": "en", "top_k_override": 3, "rag_top_k": 5}

    client.get("/search", params={"q": "news"})
    assert captured["lang"] == "en" and captured["top_k_override"] is None


def test_search_validation(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_rag(deps: Any, query: str, lang: str, rag: Any, top_k_override: int | None = None):
        raise ValueError("nope")

    monkeypatch.setattr(search_mod, "rag_search", fake_rag)
    assert client.get("/search", params={"q": "a"}).status_code == 422
    assert client.get("/search", params={"q": "ok", "lang": "de"}).status_code == 400
    assert client.get("/search", params={"q": "ok"}).status_code == 400


class FakeGraph:
    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result
        self.initial: Any = None
        self.config: Any = None

    async def ainvoke(self, initial: Any, config: Any = None) -> dict[str, Any]:
        self.initial = initial
        self.config = config
        return self.result


def test_ingest_requires_token(client: TestClient) -> None:
    assert client.post("/ingest/run").status_code == 401
    assert client.post("/ingest/run", headers={"X-Ingest-Token": "wrong"}).status_code == 401


def test_ingest_disabled_when_token_unset(app: FastAPI, client: TestClient) -> None:
    app.state.deps = make_deps(settings=make_settings(ingest_token=""))
    resp = client.post("/ingest/run", headers={"X-Ingest-Token": "anything"})
    assert resp.status_code == 503
    assert "disabled" in resp.json()["detail"]


def test_ingest_run_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGraph(
        {
            "fetched_count": 2,
            "duplicates": 5,
            "results": [
                {"id": 1, "title": "T", "category": "world", "eval_score": 8.0, "status": "processed"},
                {"title": "no-id-entry"},
            ],
            "errors": ["boom"],
        }
    )
    monkeypatch.setattr(ingest_mod, "build_pipeline_graph", lambda deps: fake)
    resp = client.post(
        "/ingest/run",
        headers={"X-Ingest-Token": "test-token"},
        json={"max_items": 10},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["fetched"] == 2
    assert body["duplicates_skipped"] == 5
    assert body["processed"] == 1
    assert body["failed"] == 1
    assert body["articles"] == [{"id": 1, "title": "T", "category": "world", "eval_score": 8.0, "status": "processed"}]
    assert body["errors"] == ["boom"]
    assert isinstance(body["duration_ms"], int)
    assert fake.initial == {"max_items": 10}
    assert fake.config == {"tags": ["ingest"], "run_name": "ingest"}


def test_ingest_run_without_body_uses_defaults(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGraph({"fetched_count": 0, "duplicates": 0, "results": [], "errors": []})
    monkeypatch.setattr(ingest_mod, "build_pipeline_graph", lambda deps: fake)
    resp = client.post("/ingest/run", headers={"X-Ingest-Token": "test-token"})
    assert resp.status_code == 200
    assert fake.initial == {}
    assert resp.json()["processed"] == 0


def test_ingest_run_validates_max_items(client: TestClient) -> None:
    resp = client.post("/ingest/run", headers={"X-Ingest-Token": "test-token"}, json={"max_items": 0})
    assert resp.status_code == 422
    resp = client.post("/ingest/run", headers={"X-Ingest-Token": "test-token"}, json={"max_items": 501})
    assert resp.status_code == 422


def test_cors_preflight_allowed_origin(client: TestClient) -> None:
    resp = client.options(
        "/articles",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_preflight_disallowed_origin(client: TestClient) -> None:
    resp = client.options(
        "/articles",
        headers={"Origin": "http://evil.example.com", "Access-Control-Request-Method": "GET"},
    )
    assert resp.status_code == 400
    assert "access-control-allow-origin" not in resp.headers
