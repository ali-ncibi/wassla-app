import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlsplit

import asyncpg
import feedparser
import httpx

from .config import Settings


@dataclass
class FeedItem:
    source_id: int
    source_name: str
    source_language: str
    url: str
    guid: str
    title: str
    body: str
    published_at: datetime | None


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return " ".join(" ".join(self.parts).split())


def html_to_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    return parser.text()


def entry_body(entry: dict[str, Any]) -> str:
    content = entry.get("content")
    if content and isinstance(content, list) and content[0].get("value"):
        return html_to_text(content[0]["value"])
    return html_to_text(entry.get("summary", "") or entry.get("description", ""))


def entry_published(entry: dict[str, Any]) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime.fromtimestamp(time.mktime(parsed), tz=None)
    return None


def feed_host(feed_url: str) -> str:
    return urlsplit(feed_url).hostname or ""


async def fetch_source(
    client: httpx.AsyncClient,
    source: dict[str, Any],
    settings: Settings,
    allowed_hosts: set[str],
) -> list[FeedItem]:
    url = source["feed_url"]
    resp = None
    for _ in range(settings.max_feed_redirects + 1):
        resp = await client.get(url, follow_redirects=False)
        if not resp.is_redirect:
            break
        location = resp.headers.get("location")
        if not location:
            break
        next_url = urljoin(url, location)
        if feed_host(next_url) not in allowed_hosts:
            msg = f"feed {source['name']} redirects to non-allowlisted host {feed_host(next_url)}"
            raise ValueError(msg)
        url = next_url
    else:
        msg = f"feed {source['name']} exceeded max redirects"
        raise ValueError(msg)
    resp.raise_for_status()
    if len(resp.content) > settings.max_feed_bytes:
        msg = f"feed {source['name']} response too large ({len(resp.content)} bytes)"
        raise ValueError(msg)
    feed = feedparser.parse(resp.content)
    items: list[FeedItem] = []
    for entry in feed.entries:
        url = entry.get("link")
        title = (entry.get("title") or "").strip()
        if not url or not title:
            continue
        body = entry_body(entry).strip()
        if len(body) < 80:
            continue
        items.append(
            FeedItem(
                source_id=source["id"],
                source_name=source["name"],
                source_language=source["language"],
                url=url,
                guid=entry.get("id", url),
                title=title,
                body=body[: settings.max_body_chars],
                published_at=entry_published(entry),
            ),
        )
    return items


async def fetch_new_items(
    pool: asyncpg.Pool,
    settings: Settings,
    max_items: int,
) -> tuple[list[FeedItem], int]:
    async with pool.acquire() as conn:
        sources = await conn.fetch("SELECT id, name, feed_url, language FROM sources WHERE active = true ORDER BY id")
        known = {r["url"] for r in await conn.fetch("SELECT url FROM articles")}
    allowed_hosts = {feed_host(s["feed_url"]) for s in sources}
    headers = {"User-Agent": settings.rss_user_agent}
    timeout = httpx.Timeout(settings.rss_timeout_seconds)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        batches = await asyncio.gather(
            *(fetch_source(client, dict(s), settings, allowed_hosts) for s in sources),
            return_exceptions=True,
        )
    fresh: list[FeedItem] = []
    duplicates = 0
    for batch in batches:
        if isinstance(batch, BaseException):
            continue
        for item in batch:
            if item.url in known:
                duplicates += 1
            elif item not in fresh:
                fresh.append(item)
    fresh.sort(key=lambda it: it.published_at or datetime.min, reverse=True)
    return fresh[:max_items], duplicates
