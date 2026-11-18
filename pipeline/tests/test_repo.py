from datetime import datetime
from typing import Any

from app import repo
from app.db import vector_literal
from app.feeds import FeedItem
from app.schemas import TranslationDraft

from .conftest import FakeConn, FakePool, as_pool

NOW = datetime(2026, 1, 1, 12, 0, 0)


def make_item(**overrides: Any) -> FeedItem:
    return FeedItem(
        source_id=1,
        source_name="S",
        source_language="en",
        url="http://example.com/a",
        guid="g",
        title="T",
        body="B",
        published_at=NOW,
        **overrides,
    )


async def test_list_sources() -> None:
    conn = FakeConn(lambda m, sql, args: [{"id": 1, "name": "S", "feed_url": "u", "language": "en"}])
    rows = await repo.list_sources(as_pool(FakePool(conn)))
    assert rows == [{"id": 1, "name": "S", "feed_url": "u", "language": "en"}]
    assert "FROM sources WHERE active = true" in conn.calls[0][1]


async def test_insert_article_pass_verdict() -> None:
    conn = FakeConn(lambda m, sql, args: 42 if m == "fetchval" else None)
    pool = as_pool(FakePool(conn))
    translations: dict[str, TranslationDraft] = {"en": {"title": "T", "body": "B"}, "fr": {"title": "Tf", "body": "Bf"}}
    summaries = {"en": "s", "fr": "sf"}
    embeddings = {"en": [0.1, 0.2], "fr": [0.3, 0.4]}
    article_id = await repo.insert_article(
        pool,
        make_item(),
        translations,
        summaries,
        embeddings,
        "world",
        {"score": 9.0, "verdict": "pass", "issues": []},
    )
    assert article_id == 42
    assert conn.transactions and conn.transactions[0].entered
    insert_call = conn.calls[0]
    assert insert_call[0] == "fetchval"
    assert "INSERT INTO articles" in insert_call[1]
    args = insert_call[2]
    assert args[1] == "http://example.com/a"
    assert args[7] == "world"
    assert args[8] == 9.0
    assert args[9] == "pass"
    assert args[10] == "[]"
    assert args[11] == "processed"
    exec_calls = [c for c in conn.calls if c[0] == "execute"]
    assert len(exec_calls) == 2
    assert "INSERT INTO article_translations" in exec_calls[0][1]
    assert exec_calls[0][2][5] == vector_literal([0.1, 0.2])
    conn2 = FakeConn(lambda m, sql, args: 7 if m == "fetchval" else None)
    single: dict[str, TranslationDraft] = {"en": {"title": "T", "body": "B"}}
    await repo.insert_article(
        as_pool(FakePool(conn2)),
        make_item(),
        single,
        {},
        {},
        "world",
        {"score": 1.0, "verdict": "review", "issues": ["bad"]},
    )
    exec2 = [c for c in conn2.calls if c[0] == "execute"]
    assert exec2[0][2][5] is None
    assert conn2.calls[0][2][11] == "needs_review"
    assert conn2.calls[0][2][10] == '["bad"]'


async def test_list_articles_with_and_without_category() -> None:
    rows = [{"id": 1, "title": "t"}]

    def router(m: str, sql: str, args: tuple[Any, ...]):
        if m == "fetchval":
            return 5
        if m == "fetch":
            return rows
        return None

    conn = FakeConn(router)
    total, out = await repo.list_articles(as_pool(FakePool(conn)), "fr", None, 24, 0)
    assert total == 5
    assert out == [{"id": 1, "title": "t"}]
    count_sql, list_sql = conn.calls[0][1], conn.calls[1][1]
    assert "AND a.category" not in count_sql
    assert conn.calls[0][2] == ("fr",)
    assert "LIMIT $2 OFFSET $3" in list_sql
    assert conn.calls[1][2] == ("fr", 24, 0)

    conn2 = FakeConn(router)
    total, out = await repo.list_articles(as_pool(FakePool(conn2)), "fr", "world", 10, 20)
    assert "AND a.category = $2" in conn2.calls[0][1]
    assert conn2.calls[0][2] == ("fr", "world")
    assert "LIMIT $3 OFFSET $4" in conn2.calls[1][1]
    assert conn2.calls[1][2] == ("fr", "world", 10, 20)


async def test_get_article_not_found() -> None:
    conn = FakeConn(lambda m, sql, args: None)
    assert await repo.get_article(as_pool(FakePool(conn)), 99, "en") is None


async def test_get_article_prefers_translation_and_lists_langs() -> None:
    row = {
        "id": 1,
        "source_language": "en",
        "url": "u",
        "published_at": NOW,
        "scraped_at": NOW,
        "category": "world",
        "eval_score": 8.0,
        "eval_verdict": "pass",
        "source_name": "S",
        "title": "Tfr",
        "body": "Bfr",
        "summary": "s",
        "lang": "fr",
    }

    def router(m: str, sql: str, args: tuple[Any, ...]):
        if m == "fetchrow":
            return row
        if m == "fetch":
            return [{"lang": "ar"}, {"lang": "en"}, {"lang": "fr"}]
        return None

    data = await repo.get_article(as_pool(FakePool(FakeConn(router))), 1, "fr")
    assert data is not None
    assert data["title"] == "Tfr"
    assert data["lang"] == "fr"
    assert data["available_langs"] == ["ar", "en", "fr"]


async def test_get_article_falls_back_to_source_language_list() -> None:
    row = {"id": 1, "source_language": "en", "lang": "en"}
    conn = FakeConn(lambda m, sql, args: row if m == "fetchrow" else ([] if m == "fetch" else None))
    data = await repo.get_article(as_pool(FakePool(conn)), 1, "en")
    assert data is not None
    assert data["available_langs"] == ["en"]


async def test_category_counts() -> None:
    conn = FakeConn(lambda m, sql, args: [{"name": "world", "count": 3}])
    assert await repo.category_counts(as_pool(FakePool(conn))) == [{"name": "world", "count": 3}]


async def test_search_translations_uses_cosine_distance() -> None:
    conn = FakeConn(lambda m, sql, args: [{"article_id": 1, "score": 0.9}])
    rows = await repo.search_translations(as_pool(FakePool(conn)), [0.1, 0.2], "ar", 5)
    assert rows == [{"article_id": 1, "score": 0.9}]
    _, sql, args = conn.calls[0]
    assert "t.embedding <=> CAST($1 AS vector)" in sql
    assert "WHERE t.lang = $2 AND t.embedding IS NOT NULL" in sql
    assert args == (vector_literal([0.1, 0.2]), "ar", 5)


async def test_stats_aggregates() -> None:
    values = iter([10, 2, 7.5, NOW])

    def router(m: str, sql: str, args: tuple[Any, ...]):
        if m == "fetchval":
            return next(values)
        if "GROUP BY" in sql:
            return [{"name": "world", "count": 6}]
        return None

    data = await repo.stats(as_pool(FakePool(FakeConn(router))))
    assert data["total_articles"] == 10
    assert data["needs_review"] == 2
    assert data["avg_eval_score"] == 7.5
    assert data["last_scraped_at"] == NOW
    assert data["by_category"] == [{"name": "world", "count": 6}]
    assert data["by_language"] == [{"name": "world", "count": 6}]


async def test_stats_handles_nulls() -> None:
    conn = FakeConn(lambda m, sql, args: None if m == "fetchval" else [])
    data = await repo.stats(as_pool(FakePool(conn)))
    assert data["total_articles"] == 0
    assert data["needs_review"] == 0
    assert data["avg_eval_score"] is None
    assert data["last_scraped_at"] is None
    assert data["by_category"] == []
