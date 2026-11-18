import json
from typing import Any

import asyncpg

from .db import vector_literal
from .feeds import FeedItem
from .schemas import TranslationDraft


async def list_sources(pool: asyncpg.Pool) -> list[dict[str, Any]]:
    async with pool.acquire() as conn:
        return [
            dict(r)
            for r in await conn.fetch(
                "SELECT id, name, feed_url, language FROM sources WHERE active = true ORDER BY id",
            )
        ]


async def insert_article(
    pool: asyncpg.Pool,
    item: FeedItem,
    translations: dict[str, TranslationDraft],
    summaries: dict[str, str],
    embeddings: dict[str, list[float]],
    category: str,
    evaluation: dict[str, Any],
) -> int:
    score = float(evaluation.get("score", 0))
    verdict = str(evaluation.get("verdict", "review"))
    feedback = json.dumps(evaluation.get("issues", []), ensure_ascii=False)
    status = "processed" if verdict == "pass" else "needs_review"
    async with pool.acquire() as conn, conn.transaction():
        article_id: int = await conn.fetchval(
            """
                INSERT INTO articles
                    (source_id, url, guid, source_language, title, body, summary, category,
                     eval_score, eval_verdict, eval_feedback, status, published_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                RETURNING id
                """,
            item.source_id,
            item.url,
            item.guid,
            item.source_language,
            item.title,
            item.body,
            summaries.get(item.source_language),
            category,
            score,
            verdict,
            feedback,
            status,
            item.published_at,
        )
        for lang, tr in translations.items():
            emb = embeddings.get(lang)
            await conn.execute(
                """
                    INSERT INTO article_translations (article_id, lang, title, body, summary, embedding)
                    VALUES ($1,$2,$3,$4,$5, CAST($6 AS vector))
                    ON CONFLICT (article_id, lang) DO NOTHING
                    """,
                article_id,
                lang,
                tr["title"],
                tr["body"],
                summaries.get(lang),
                vector_literal(emb) if emb else None,
            )
    return article_id


async def list_articles(
    pool: asyncpg.Pool,
    lang: str,
    category: str | None,
    limit: int,
    offset: int,
) -> tuple[int, list[dict[str, Any]]]:
    where_cat = "AND a.category = $2" if category else ""
    args_cat = [lang, category, limit, offset] if category else [lang, limit, offset]
    async with pool.acquire() as conn:
        total = await conn.fetchval(
            f"SELECT count(*) FROM articles a JOIN article_translations t ON t.article_id = a.id AND t.lang = $1 "
            f"WHERE 1=1 {where_cat}",
            *([lang, category] if category else [lang]),
        )
        rows = await conn.fetch(
            f"""
            SELECT a.id, t.title, t.summary, a.category, s.name AS source_name, a.url,
                   a.published_at, a.scraped_at
            FROM articles a
            JOIN article_translations t ON t.article_id = a.id AND t.lang = $1
            JOIN sources s ON s.id = a.source_id
            WHERE 1=1 {where_cat}
            ORDER BY COALESCE(a.published_at, a.scraped_at) DESC, a.id DESC
            LIMIT ${len(args_cat) - 1} OFFSET ${len(args_cat)}
            """,
            *args_cat,
        )
    return total, [dict(r) for r in rows]


async def get_article(pool: asyncpg.Pool, article_id: int, lang: str) -> dict[str, Any] | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT a.id, a.source_language, a.url, a.published_at, a.scraped_at, a.category,
                   a.eval_score, a.eval_verdict, s.name AS source_name,
                   COALESCE(t.title, a.title) AS title,
                   COALESCE(t.body, a.body) AS body,
                   COALESCE(t.summary, a.summary) AS summary,
                   COALESCE(t.lang, a.source_language) AS lang
            FROM articles a
            JOIN sources s ON s.id = a.source_id
            LEFT JOIN article_translations t ON t.article_id = a.id AND t.lang = $2
            WHERE a.id = $1
            """,
            article_id,
            lang,
        )
        if not row:
            return None
        langs = await conn.fetch(
            "SELECT lang FROM article_translations WHERE article_id = $1 ORDER BY lang",
            article_id,
        )
    data = dict(row)
    data["available_langs"] = [r["lang"] for r in langs] or [data["source_language"]]
    return data


async def category_counts(pool: asyncpg.Pool) -> list[dict[str, Any]]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT COALESCE(category, 'uncategorized') AS name, count(*)::int AS count FROM articles "
            "GROUP BY 1 ORDER BY 2 DESC",
        )
    return [dict(r) for r in rows]


async def search_translations(
    pool: asyncpg.Pool,
    query_vec: list[float],
    lang: str,
    top_k: int,
) -> list[dict[str, Any]]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT t.article_id, t.title, t.summary, a.category, a.url, a.published_at,
                   s.name AS source_name,
                   1 - (t.embedding <=> CAST($1 AS vector)) AS score
            FROM article_translations t
            JOIN articles a ON a.id = t.article_id
            JOIN sources s ON s.id = a.source_id
            WHERE t.lang = $2 AND t.embedding IS NOT NULL
            ORDER BY t.embedding <=> CAST($1 AS vector)
            LIMIT $3
            """,
            vector_literal(query_vec),
            lang,
            top_k,
        )
    return [dict(r) for r in rows]


async def stats(pool: asyncpg.Pool) -> dict[str, Any]:
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT count(*) FROM articles")
        needs_review = await conn.fetchval("SELECT count(*) FROM articles WHERE status = 'needs_review'")
        avg_score = await conn.fetchval("SELECT avg(eval_score) FROM articles WHERE eval_score IS NOT NULL")
        last = await conn.fetchval("SELECT max(scraped_at) FROM articles")
        by_cat = await conn.fetch(
            "SELECT COALESCE(category,'uncategorized') AS name, count(*)::int AS count FROM articles "
            "GROUP BY 1 ORDER BY 2 DESC",
        )
        by_lang = await conn.fetch(
            "SELECT lang AS name, count(*)::int AS count FROM article_translations GROUP BY 1 ORDER BY 2 DESC",
        )
    return {
        "total_articles": total or 0,
        "needs_review": needs_review or 0,
        "avg_eval_score": float(avg_score) if avg_score is not None else None,
        "last_scraped_at": last,
        "by_category": [dict(r) for r in by_cat],
        "by_language": [dict(r) for r in by_lang],
    }
