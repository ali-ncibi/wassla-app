import json
from typing import Any

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from app.feeds import FeedItem
from app.graph import nodes
from app.graph.nodes import (
    call_llm,
    make_categorize_node,
    make_embed_node,
    make_evaluate_node,
    make_fetch_node,
    make_persist_node,
    make_process_article_node,
    make_summarize_node,
    make_translate_node,
    parse_json_object,
)
from app.providers.embeddings import StubEmbeddings

from .conftest import make_deps, make_settings


class FakeChat(BaseChatModel):
    responses: list[Any] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "fake-chat"

    def _generate(self, messages: Any, stop: Any = None, run_manager: Any = None, **kwargs: Any) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self.responses.pop(0)))])


def make_item(**overrides: Any) -> FeedItem:
    base: dict[str, Any] = {
        "source_id": 1,
        "source_name": "S",
        "source_language": "en",
        "url": "http://example.com/a",
        "guid": "g",
        "title": "Title",
        "body": "Body text " * 20,
        "published_at": None,
    }
    base.update(overrides)
    return FeedItem(**base)


def test_parse_json_object_plain() -> None:
    assert parse_json_object('{"a": 1}') == {"a": 1}


def test_parse_json_object_with_surrounding_text() -> None:
    assert parse_json_object('Sure! Here you go:\n{"a": 1}\nthanks') == {"a": 1}


def test_parse_json_object_repairs_missing_closing_braces() -> None:
    assert parse_json_object('{"a": {"b": 1}') == {"a": {"b": 1}}


def test_parse_json_object_rejects_non_json() -> None:
    with pytest.raises(ValueError, match="not a JSON object"):
        parse_json_object("no json at all")
    with pytest.raises(ValueError, match="not a JSON object"):
        parse_json_object("{not valid json,,,,")


async def test_call_llm_returns_string_content() -> None:
    deps = make_deps(chat={"translate": FakeChat(responses=["hello"])})
    assert await call_llm(deps, "translate", [HumanMessage(content="x")]) == "hello"


async def test_call_llm_serializes_non_string_content() -> None:
    blocks = [{"type": "text", "text": "x"}]
    deps = make_deps(chat={"translate": FakeChat(responses=[blocks])})
    assert await call_llm(deps, "translate", [HumanMessage(content="x")]) == json.dumps(blocks)


class RecordingChat:
    def __init__(self) -> None:
        self.config: Any = None

    async def ainvoke(self, messages: Any, config: Any = None) -> Any:
        self.config = config
        return AIMessage(content="ok")


async def test_call_llm_tags_run_with_task() -> None:
    rec = RecordingChat()
    deps = make_deps(chat={"summarize": rec})
    assert await call_llm(deps, "summarize", [HumanMessage(content="x")]) == "ok"
    assert rec.config == {"tags": ["task:summarize"], "metadata": {"task": "summarize"}}


async def test_translate_node_reuses_source_language_and_translates_others() -> None:
    deps = make_deps()
    node = make_translate_node(deps)
    result = await node({"item": make_item()})
    translations = result["translations"]
    assert set(translations) == {"en", "fr", "ar"}
    assert translations["en"] == {"title": "Title", "body": make_item().body}
    assert translations["fr"]["title"].startswith("[fr] ")
    assert translations["ar"]["title"].startswith("[ar] ")


async def test_translate_node_parses_llm_json() -> None:
    deps = make_deps(
        chat={
            "translate": FakeChat(
                responses=[
                    json.dumps({"title": "Tfr", "body": "Bfr"}),
                    json.dumps({"title": "Tar", "body": "Bar"}),
                ]
            )
        }
    )
    node = make_translate_node(deps)
    result = await node({"item": make_item()})
    assert result["translations"]["fr"] == {"title": "Tfr", "body": "Bfr"}
    assert result["translations"]["ar"] == {"title": "Tar", "body": "Bar"}


async def test_categorize_node_accepts_valid_category() -> None:
    deps = make_deps(chat={"categorize": FakeChat(responses=['{"category": "sports", "confidence": 0.9}'])})
    result = await make_categorize_node(deps)({"item": make_item()})
    assert result["category"] == "sports"


async def test_categorize_node_falls_back_on_unknown_category() -> None:
    deps = make_deps(chat={"categorize": FakeChat(responses=['{"category": "bogus", "confidence": 0.1}'])})
    result = await make_categorize_node(deps)({"item": make_item()})
    assert result["category"] == "world"


async def test_summarize_node_summarizes_each_translation() -> None:
    deps = make_deps()
    node = make_summarize_node(deps)
    state = {"translations": {"en": {"title": "T", "body": "b " * 100}, "fr": {"title": "Tf", "body": "bf " * 100}}}
    result = await node(state)  # type: ignore[arg-type]
    assert set(result["summaries"]) == {"en", "fr"}
    assert all(len(s.split()) == 60 for s in result["summaries"].values())


async def test_evaluate_node_clamps_score_and_derives_verdict() -> None:
    deps = make_deps(
        settings=make_settings(eval_min_score=6.0),
        chat={"evaluate": FakeChat(responses=['{"score": 99, "verdict": "pass", "issues": ["x"]}'])},
    )
    result = await make_evaluate_node(deps)(
        {  # type: ignore[arg-type]
            "item": make_item(),
            "translations": {"en": {"title": "T", "body": "B"}},
            "summaries": {"en": "s"},
            "category": "world",
        }
    )
    assert result["evaluation"] == {"score": 10.0, "verdict": "pass", "issues": ["x"]}


async def test_evaluate_node_low_score_means_review_and_defaults() -> None:
    deps = make_deps(chat={"evaluate": FakeChat(responses=["{}"])})
    result = await make_evaluate_node(deps)(
        {  # type: ignore[arg-type]
            "item": make_item(),
            "translations": {"en": {"title": "T", "body": "B"}},
            "summaries": {},
            "category": "world",
        }
    )
    assert result["evaluation"] == {"score": 0.0, "verdict": "review", "issues": []}

    deps2 = make_deps(chat={"evaluate": FakeChat(responses=['{"score": 3, "issues": ["meh"]}'])})
    result2 = await make_evaluate_node(deps2)(
        {  # type: ignore[arg-type]
            "item": make_item(),
            "translations": {"en": {"title": "T", "body": "B"}},
            "summaries": {},
            "category": "world",
        }
    )
    assert result2["evaluation"]["verdict"] == "review"
    assert result2["evaluation"]["issues"] == ["meh"]


async def test_embed_node_embeds_each_language() -> None:
    deps = make_deps(embedder=StubEmbeddings(dim=1024))
    node = make_embed_node(deps)
    state = {
        "translations": {"en": {"title": "T", "body": "b"}, "ar": {"title": "Ta", "body": "ba"}},
        "summaries": {"en": "s", "ar": "sa"},
    }
    result = await node(state)  # type: ignore[arg-type]
    assert set(result["embeddings"]) == {"en", "ar"}
    assert all(len(v) == 1024 for v in result["embeddings"].values())


async def test_persist_node_delegates_to_repo(monkeypatch) -> None:
    captured = {}

    async def fake_insert(pool, item, translations, summaries, embeddings, category, evaluation):
        captured.update(item=item, translations=translations, category=category, evaluation=evaluation)
        return 123

    monkeypatch.setattr(nodes.repo, "insert_article", fake_insert)
    deps = make_deps()
    state = {
        "item": make_item(),
        "translations": {"en": {"title": "T", "body": "B"}},
        "summaries": {"en": "s"},
        "embeddings": {"en": [0.1]},
        "category": "world",
        "evaluation": {"score": 8.0, "verdict": "pass", "issues": []},
    }
    result = await make_persist_node(deps)(state)  # type: ignore[arg-type]
    assert result == {"article_id": 123}
    assert captured["category"] == "world"
    assert captured["item"].url == "http://example.com/a"


async def test_fetch_node_uses_state_max_items_or_default(monkeypatch) -> None:
    seen = {}

    async def fake_fetch(pool, settings, max_items):
        seen["max_items"] = max_items
        return [make_item()], 7

    monkeypatch.setattr(nodes, "fetch_new_items", fake_fetch)
    deps = make_deps(settings=make_settings(ingest_max_items=50))
    node = make_fetch_node(deps)
    result = await node({})
    assert seen["max_items"] == 50
    assert result["fetched_count"] == 1
    assert result["duplicates"] == 7
    assert len(result["items"]) == 1
    result2 = await node({"max_items": 5})
    assert seen["max_items"] == 5
    assert result2["fetched_count"] == 1


async def test_require_raises_on_missing_state_key() -> None:
    deps = make_deps()
    node = make_summarize_node(deps)
    with pytest.raises(KeyError, match="missing required graph state key"):
        await node({})


class FakeArticleGraph:
    def __init__(self, result: dict[str, Any] | None = None, exc: Exception | None = None) -> None:
        self.result = result
        self.exc = exc
        self.config: Any = None

    async def ainvoke(self, state: dict[str, Any], config: Any = None) -> dict[str, Any]:
        self.config = config
        if self.exc is not None:
            raise self.exc
        return self.result  # type: ignore[return-value]


async def test_process_article_node_success() -> None:
    deps = make_deps()
    graph = FakeArticleGraph(
        {
            "article_id": 9,
            "category": "world",
            "evaluation": {"score": 8.5, "verdict": "pass"},
        }
    )
    node = make_process_article_node(graph, deps)  # type: ignore[arg-type]
    result = await node({"item": make_item()})
    assert result["results"] == [
        {
            "id": 9,
            "title": "Title",
            "category": "world",
            "eval_score": 8.5,
            "status": "processed",
        }
    ]
    assert "errors" not in result
    assert graph.config["tags"] == ["article"]
    assert graph.config["metadata"]["article_url"] == "http://example.com/a"


async def test_process_article_node_review_status_and_error_collection() -> None:
    deps = make_deps()
    graph = FakeArticleGraph(
        {
            "article_id": 10,
            "category": "sports",
            "evaluation": {"score": 2.0, "verdict": "review"},
        }
    )
    node = make_process_article_node(graph, deps)  # type: ignore[arg-type]
    result = await node({"item": make_item()})
    assert result["results"][0]["status"] == "needs_review"

    bad = make_process_article_node(FakeArticleGraph(exc=RuntimeError("kaput")), deps)  # type: ignore[arg-type]
    result2 = await bad({"item": make_item()})
    assert result2["errors"] == ["http://example.com/a: RuntimeError: kaput"]
    assert "results" not in result2
