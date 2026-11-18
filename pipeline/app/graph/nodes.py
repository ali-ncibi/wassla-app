import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, cast

import asyncpg
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langgraph.graph.state import CompiledStateGraph
from openinference.instrumentation import using_metadata, using_tags

from .. import repo
from ..config import Settings
from ..feeds import FeedItem, fetch_new_items
from .prompts import categorize_messages, evaluate_messages, summarize_messages, translate_messages
from .state import ArticleState, require

ArticleNode = Callable[..., Awaitable[dict[str, Any]]]
PipelineNode = Callable[..., Awaitable[dict[str, Any]]]


@dataclass
class Deps:
    settings: Settings
    pool: asyncpg.Pool
    chat: dict[str, BaseChatModel]
    embedder: Embeddings
    semaphore: asyncio.Semaphore


async def call_llm(deps: Deps, task: str, messages: list[BaseMessage]) -> str:
    async with deps.semaphore:
        with using_tags([f"task:{task}"]), using_metadata({"task": task}):
            resp = await deps.chat[task].ainvoke(
                messages,
                config={"tags": [f"task:{task}"], "metadata": {"task": task}},
            )
    return resp.content if isinstance(resp.content, str) else json.dumps(resp.content)


def parse_json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    if start == -1:
        msg = f"LLM response is not a JSON object: {text[:200]}"
        raise ValueError(msg)
    chunk = text[start:]
    try:
        obj, _ = json.JSONDecoder().raw_decode(chunk)
    except json.JSONDecodeError:
        for extra in range(1, 32):
            try:
                return cast("dict[str, Any]", json.loads(chunk + "}" * extra))
            except json.JSONDecodeError:
                continue
        msg = f"LLM response is not a JSON object: {text[:200]}"
        raise ValueError(msg) from None
    else:
        return cast("dict[str, Any]", obj)


def make_translate_node(deps: Deps) -> ArticleNode:
    async def node(state: ArticleState) -> dict[str, Any]:
        item = require(state, "item")
        langs = deps.settings.language_list

        async def one(lang: str) -> tuple[str, dict[str, str]]:
            if lang == item.source_language:
                return lang, {"title": item.title, "body": item.body}
            out = await call_llm(deps, "translate", translate_messages(lang, item.title, item.body))
            data = parse_json_object(out)
            return lang, {"title": str(data["title"]), "body": str(data["body"])}

        translations = dict(await asyncio.gather(*(one(lang) for lang in langs)))
        return {"translations": translations}

    return node


def make_categorize_node(deps: Deps) -> ArticleNode:
    async def node(state: ArticleState) -> dict[str, Any]:
        item = require(state, "item")
        out = await call_llm(
            deps,
            "categorize",
            categorize_messages(deps.settings.category_list, item.title, item.body),
        )
        data = parse_json_object(out)
        category = str(data.get("category", "")).strip().lower()
        if category not in deps.settings.category_list:
            category = deps.settings.category_list[0]
        return {"category": category}

    return node


def make_summarize_node(deps: Deps) -> ArticleNode:
    async def node(state: ArticleState) -> dict[str, Any]:
        translations = require(state, "translations")

        async def one(lang: str) -> tuple[str, str]:
            tr = translations[lang]
            out = await call_llm(deps, "summarize", summarize_messages(lang, tr["title"], tr["body"]))
            return lang, out.strip()

        summaries = dict(await asyncio.gather(*(one(lang) for lang in translations)))
        return {"summaries": summaries}

    return node


def make_evaluate_node(deps: Deps) -> ArticleNode:
    async def node(state: ArticleState) -> dict[str, Any]:
        item = require(state, "item")
        original = {"title": item.title, "body": item.body[:2000]}
        out = await call_llm(
            deps,
            "evaluate",
            evaluate_messages(
                item.source_language,
                original,
                require(state, "translations"),
                require(state, "summaries"),
                require(state, "category"),
            ),
        )
        data = parse_json_object(out)
        score = max(0.0, min(10.0, float(data.get("score", 0))))
        verdict = "pass" if score >= deps.settings.eval_min_score else "review"
        return {"evaluation": {"score": score, "verdict": verdict, "issues": data.get("issues", [])}}

    return node


def make_embed_node(deps: Deps) -> ArticleNode:
    async def node(state: ArticleState) -> dict[str, Any]:
        translations = require(state, "translations")
        summaries = require(state, "summaries")
        langs = list(translations.keys())
        texts = [
            f"{translations[lang]['title']}\n\n{summaries.get(lang, '')}\n\n{translations[lang]['body'][:6000]}"
            for lang in langs
        ]
        async with deps.semaphore:
            vecs = await deps.embedder.aembed_documents(texts)
        return {"embeddings": dict(zip(langs, vecs, strict=True))}

    return node


def make_persist_node(deps: Deps) -> ArticleNode:
    async def node(state: ArticleState) -> dict[str, Any]:
        article_id = await repo.insert_article(
            deps.pool,
            require(state, "item"),
            require(state, "translations"),
            require(state, "summaries"),
            require(state, "embeddings"),
            require(state, "category"),
            require(state, "evaluation"),
        )
        return {"article_id": article_id}

    return node


def make_fetch_node(deps: Deps) -> PipelineNode:
    async def node(state: dict[str, Any]) -> dict[str, Any]:
        max_items = state.get("max_items") or deps.settings.ingest_max_items
        items, duplicates = await fetch_new_items(deps.pool, deps.settings, max_items)
        return {"items": items, "fetched_count": len(items), "duplicates": duplicates}

    return node


def make_process_article_node(article_graph: CompiledStateGraph[ArticleState], deps: Deps) -> PipelineNode:
    async def node(state: dict[str, Any]) -> dict[str, Any]:
        item: FeedItem = state["item"]
        try:
            with using_tags(["article"]), using_metadata({"article_url": item.url}):
                result = await article_graph.ainvoke(
                    {"item": item},
                    config={"tags": ["article"], "metadata": {"article_url": item.url}},
                )
            return {
                "results": [
                    {
                        "id": result["article_id"],
                        "title": item.title[:120],
                        "category": result["category"],
                        "eval_score": result["evaluation"]["score"],
                        "status": "processed" if result["evaluation"]["verdict"] == "pass" else "needs_review",
                    },
                ],
            }
        except Exception as exc:
            return {"errors": [f"{item.url}: {type(exc).__name__}: {exc}"]}

    return node
