from typing import Any

import pytest

from app import repo
from app.rag import rag_search
from app.schemas import RagConfig

from .conftest import make_deps


def make_rows(scores: list[float]) -> list[dict[str, Any]]:
    return [
        {
            "article_id": i + 1,
            "title": f"Title {i}",
            "summary": f"summary {i}",
            "category": "world",
            "url": f"http://example.com/{i}",
            "published_at": None,
            "source_name": "S",
            "score": s,
        }
        for i, s in enumerate(scores)
    ]


async def test_rag_search_filters_by_min_score_and_generates_answer(monkeypatch) -> None:
    captured = {}

    async def fake_search(pool, query_vec, lang, top_k):
        captured.update(lang=lang, top_k=top_k, vec_len=len(query_vec))
        return make_rows([0.9, 0.35, 0.2])

    monkeypatch.setattr(repo, "search_translations", fake_search)
    deps = make_deps()
    rag = RagConfig(top_k=5, min_score=0.35, answer_enabled=True)
    result = await rag_search(deps, "what happened?", "en", rag)
    assert captured["lang"] == "en"
    assert captured["top_k"] == 5
    assert captured["vec_len"] == 1024
    assert [h.article_id for h in result.hits] == [1, 2]
    assert result.hits[0].score == 0.9
    assert result.answer == "stub response"
    assert result.query == "what happened?"
    assert result.lang == "en"


async def test_rag_search_top_k_override(monkeypatch) -> None:
    captured = {}

    async def fake_search(pool, query_vec, lang, top_k):
        captured["top_k"] = top_k
        return make_rows([0.9])

    monkeypatch.setattr(repo, "search_translations", fake_search)
    deps = make_deps()
    rag = RagConfig(top_k=5, min_score=0.35, answer_enabled=False)
    result = await rag_search(deps, "q", "fr", rag, top_k_override=3)
    assert captured["top_k"] == 3
    assert result.answer is None
    assert len(result.hits) == 1


async def test_rag_search_rejects_unsupported_language() -> None:
    deps = make_deps()
    rag = RagConfig(top_k=5, min_score=0.35, answer_enabled=True)
    with pytest.raises(ValueError, match="Unsupported language: de"):
        await rag_search(deps, "q", "de", rag)


async def test_rag_search_no_hits_means_no_answer(monkeypatch) -> None:
    async def fake_search(pool, query_vec, lang, top_k):
        return []

    monkeypatch.setattr(repo, "search_translations", fake_search)
    deps = make_deps()
    rag = RagConfig(top_k=5, min_score=0.35, answer_enabled=True)
    result = await rag_search(deps, "q", "ar", rag)
    assert result.hits == []
    assert result.answer is None
