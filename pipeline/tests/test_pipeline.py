from typing import Any

import pytest

from app.graph import nodes
from app.graph.pipeline import build_article_graph, build_pipeline_graph, route_to_articles

from .conftest import make_deps
from .test_nodes import make_item


async def test_article_graph_end_to_end_with_stubs(monkeypatch) -> None:
    inserted = {}

    async def fake_insert(pool, item, translations, summaries, embeddings, category, evaluation):
        inserted.update(
            translations=translations,
            category=category,
            evaluation=evaluation,
            embeddings=embeddings,
            summaries=summaries,
        )
        return 42

    monkeypatch.setattr("app.repo.insert_article", fake_insert)
    deps = make_deps()
    graph = build_article_graph(deps)
    final = await graph.ainvoke({"item": make_item()})
    assert final["article_id"] == 42
    assert set(final["translations"]) == {"en", "fr", "ar"}
    assert final["category"] in deps.settings.category_list
    assert set(final["summaries"]) == {"en", "fr", "ar"}
    assert final["evaluation"]["verdict"] == "pass"
    assert set(final["embeddings"]) == {"en", "fr", "ar"}
    assert inserted["category"] == final["category"]


async def test_article_graph_without_persist_skips_db(monkeypatch) -> None:
    def boom(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("persist node must not run when persist=False")

    monkeypatch.setattr("app.repo.insert_article", boom)
    deps = make_deps()
    graph = build_article_graph(deps, persist=False)
    final = await graph.ainvoke({"item": make_item()})
    assert "article_id" not in final
    assert final["category"] in deps.settings.category_list
    assert set(final["translations"]) == {"en", "fr", "ar"}


def test_route_to_articles_requires_items_key() -> None:
    with pytest.raises(KeyError, match="missing required graph state key"):
        route_to_articles({})


async def test_route_to_articles_sends_one_per_item() -> None:
    items = [make_item(url="http://example.com/1"), make_item(url="http://example.com/2")]
    sends = route_to_articles({"items": items})  # type: ignore[typeddict-item]
    assert len(sends) == 2
    assert all(s.node == "process_article" for s in sends)
    assert sends[0].arg == {"item": items[0]}
    assert sends[1].arg == {"item": items[1]}


async def test_pipeline_graph_fans_out_and_aggregates(monkeypatch) -> None:
    async def fake_fetch(pool, settings, max_items):
        assert max_items == 50
        return [make_item(url="http://example.com/1"), make_item(url="http://example.com/2")], 3

    monkeypatch.setattr(nodes, "fetch_new_items", fake_fetch)

    counter = {"n": 0}

    async def fake_insert(pool, item, translations, summaries, embeddings, category, evaluation):
        counter["n"] += 1
        return counter["n"]

    monkeypatch.setattr("app.repo.insert_article", fake_insert)

    deps = make_deps()
    graph = build_pipeline_graph(deps)
    final = await graph.ainvoke({})
    assert final["fetched_count"] == 2
    assert final["duplicates"] == 3
    assert len(final["results"]) == 2
    assert {r["id"] for r in final["results"]} == {1, 2}
    assert final["errors"] == []
    assert all(r["status"] == "processed" for r in final["results"])


async def test_pipeline_graph_collects_errors_per_article(monkeypatch) -> None:
    async def fake_fetch(pool, settings, max_items):
        return [make_item(url="http://example.com/ok"), make_item(url="http://example.com/fail")], 0

    monkeypatch.setattr(nodes, "fetch_new_items", fake_fetch)

    async def fake_insert(pool, item, translations, summaries, embeddings, category, evaluation):
        if "fail" in item.url:
            raise RuntimeError("db down")
        return 1

    monkeypatch.setattr("app.repo.insert_article", fake_insert)

    deps = make_deps()
    graph = build_pipeline_graph(deps)
    final = await graph.ainvoke({"max_items": 10})
    assert len(final["results"]) == 1
    assert final["results"][0]["id"] == 1
    assert len(final["errors"]) == 1
    assert "http://example.com/fail" in final["errors"][0]
    assert "RuntimeError" in final["errors"][0]
