import time
from typing import Any, cast

import httpx
import pytest

from app.feeds import (
    FeedItem,
    entry_body,
    entry_published,
    feed_host,
    fetch_new_items,
    fetch_source,
    html_to_text,
)

from .conftest import FakeConn, FakePool, as_pool, make_settings

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test</title>
<item>
  <link>http://example.com/a</link>
  <title>Article A</title>
  <guid>guid-a</guid>
  <pubDate>Wed, 01 Jan 2026 10:00:00 GMT</pubDate>
  <description>&lt;p&gt;{body_a}&lt;/p&gt;</description>
</item>
<item>
  <link>http://example.com/b</link>
  <title>Article B</title>
  <description>short</description>
</item>
<item>
  <title>No link</title>
  <description>{body_c}</description>
</item>
<item>
  <link>http://example.com/d</link>
  <title>Article D</title>
  <pubDate>Fri, 02 Jan 2026 10:00:00 GMT</pubDate>
  <content type="html">&lt;p&gt;{body_d}&lt;/p&gt;</content>
</item>
</channel></rss>
"""

BODY_A = "word " * 30
BODY_C = "word " * 30
BODY_D = "word " * 30


def rss(host: str = "example.com", body_a: str = BODY_A, body_c: str = BODY_C, body_d: str = BODY_D) -> bytes:
    xml = RSS.format(body_a=body_a, body_c=body_c, body_d=body_d)
    return xml.replace("http://example.com/", f"http://{host}/").encode()


class FakeResponse:
    def __init__(
        self,
        content: bytes = b"",
        is_redirect: bool = False,
        headers: dict[str, str] | None = None,
        raise_exc: Exception | None = None,
    ) -> None:
        self.content = content
        self.is_redirect = is_redirect
        self.headers = headers or {}
        self._raise_exc = raise_exc

    def raise_for_status(self) -> None:
        if self._raise_exc is not None:
            raise self._raise_exc


class FakeHttpClient:
    """Scripted responses: list of FakeResponse consumed in order per get() call."""

    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.requested: list[str] = []

    async def get(self, url: str, follow_redirects: bool = False) -> FakeResponse:
        self.requested.append(url)
        assert follow_redirects is False
        return self.responses.pop(0)


def as_client(client: FakeHttpClient) -> httpx.AsyncClient:
    """Cast a FakeHttpClient to httpx.AsyncClient for fetch_source call sites."""
    return cast("httpx.AsyncClient", client)


def make_source(**overrides: Any) -> dict[str, Any]:
    return {"id": 1, "name": "Test Source", "feed_url": "http://example.com/rss", "language": "en", **overrides}


def test_html_to_text_strips_tags_and_collapses_whitespace() -> None:
    assert html_to_text("<p>Hello <b>world</b></p>  <p>again</p>") == "Hello world again"
    assert html_to_text("") == ""


def test_entry_body_prefers_content_over_summary() -> None:
    entry = {"content": [{"value": "<p>full body</p>"}], "summary": "short summary"}
    assert entry_body(entry) == "full body"
    assert entry_body({"summary": "<i>sum</i>"}) == "sum"
    assert entry_body({"description": "desc"}) == "desc"
    assert entry_body({}) == ""


def test_entry_published_prefers_published_then_updated() -> None:
    from datetime import datetime

    published = time.struct_time((2026, 1, 1, 10, 0, 0, 3, 1, 0))
    updated = time.struct_time((2026, 2, 2, 10, 0, 0, 0, 33, 0))
    expected_published = datetime.fromtimestamp(time.mktime(published))
    expected_updated = datetime.fromtimestamp(time.mktime(updated))
    assert entry_published({"published_parsed": published}) == expected_published
    assert entry_published({"published_parsed": published, "updated_parsed": updated}) == expected_published
    assert entry_published({"updated_parsed": updated}) == expected_updated
    assert entry_published({}) is None


def test_feed_host() -> None:
    assert feed_host("https://feeds.bbci.co.uk/news/rss.xml") == "feeds.bbci.co.uk"
    assert feed_host("notaurl") == ""


async def test_fetch_source_parses_entries_and_filters() -> None:
    settings = make_settings()
    client = FakeHttpClient([FakeResponse(content=rss())])
    items = await fetch_source(as_client(client), make_source(), settings, {"example.com"})
    assert [i.url for i in items] == ["http://example.com/a", "http://example.com/d"]
    a = items[0]
    assert isinstance(a, FeedItem)
    assert a.source_id == 1
    assert a.source_name == "Test Source"
    assert a.source_language == "en"
    assert a.guid == "guid-a"
    assert a.title == "Article A"
    assert a.body.startswith("word word")
    assert a.published_at is not None
    assert items[1].guid == "http://example.com/d"


async def test_fetch_source_truncates_body_to_max_body_chars() -> None:
    settings = make_settings(max_body_chars=100)
    client = FakeHttpClient([FakeResponse(content=rss(body_a="x" * 500))])
    items = await fetch_source(as_client(client), make_source(), settings, {"example.com"})
    assert len(items[0].body) == 100


async def test_fetch_source_follows_redirect_to_allowlisted_host() -> None:
    settings = make_settings()
    client = FakeHttpClient(
        [
            FakeResponse(is_redirect=True, headers={"location": "https://example.com/rss"}),
            FakeResponse(content=rss()),
        ]
    )
    items = await fetch_source(as_client(client), make_source(), settings, {"example.com"})
    assert client.requested == ["http://example.com/rss", "https://example.com/rss"]
    assert len(items) == 2


async def test_fetch_source_rejects_redirect_to_non_allowlisted_host() -> None:
    settings = make_settings()
    client = FakeHttpClient([FakeResponse(is_redirect=True, headers={"location": "http://evil.com/x"})])
    with pytest.raises(ValueError, match="non-allowlisted host evil.com"):
        await fetch_source(as_client(client), make_source(), settings, {"example.com"})


async def test_fetch_source_rejects_redirect_without_location() -> None:
    settings = make_settings()
    client = FakeHttpClient([FakeResponse(is_redirect=True, headers={}, raise_exc=RuntimeError("3xx"))])
    with pytest.raises(RuntimeError, match="3xx"):
        await fetch_source(as_client(client), make_source(), settings, {"example.com"})


async def test_fetch_source_exceeds_max_redirects() -> None:
    settings = make_settings(max_feed_redirects=2)
    client = FakeHttpClient(
        [FakeResponse(is_redirect=True, headers={"location": "http://example.com/r2"}) for _ in range(3)]
    )
    with pytest.raises(ValueError, match="exceeded max redirects"):
        await fetch_source(as_client(client), make_source(), settings, {"example.com"})


async def test_fetch_source_rejects_oversized_response() -> None:
    settings = make_settings(max_feed_bytes=10)
    client = FakeHttpClient([FakeResponse(content=b"x" * 100)])
    with pytest.raises(ValueError, match="too large"):
        await fetch_source(as_client(client), make_source(), settings, {"example.com"})


async def test_fetch_source_propagates_http_status_errors() -> None:
    settings = make_settings()
    client = FakeHttpClient([FakeResponse(raise_exc=RuntimeError("404"))])
    with pytest.raises(RuntimeError, match="404"):
        await fetch_source(as_client(client), make_source(), settings, {"example.com"})


class _FakeAsyncClientCM:
    """Mimics httpx.AsyncClient as an async context manager with scripted responses."""

    responses: list[FakeResponse] = []
    fail_hosts: set[str] = set()

    def __init__(self, headers: dict[str, str] | None = None, timeout: Any = None) -> None:
        self.headers = headers
        self.timeout = timeout

    async def __aenter__(self) -> "_FakeAsyncClientCM":
        return self

    async def __aexit__(self, *args: Any) -> bool:
        return False

    async def get(self, url: str, follow_redirects: bool = False) -> FakeResponse:
        if any(host in url for host in _FakeAsyncClientCM.fail_hosts):
            raise RuntimeError(f"boom {url}")
        return _FakeAsyncClientCM.responses.pop(0)


async def test_fetch_new_items_dedupes_sorts_and_caps(monkeypatch) -> None:
    import app.feeds as feeds_mod

    monkeypatch.setattr(feeds_mod.httpx, "AsyncClient", _FakeAsyncClientCM)
    settings = make_settings()

    sources = [
        {"id": 1, "name": "S1", "feed_url": "http://example.com/rss", "language": "en"},
        {"id": 2, "name": "S2", "feed_url": "http://other.com/feed", "language": "fr"},
    ]

    def router(method: str, sql: str, args: tuple[Any, ...]) -> Any:
        if "FROM sources" in sql:
            return sources
        if "SELECT url FROM articles" in sql:
            return [{"url": "http://example.com/a"}, {"url": "http://other.com/a"}]
        return None

    conn = FakeConn(router)
    pool = as_pool(FakePool(conn))

    rss_no_date = rss(host="other.com").replace(b"<pubDate>Fri, 02 Jan 2026 10:00:00 GMT</pubDate>", b"")
    _FakeAsyncClientCM.responses = [FakeResponse(content=rss()), FakeResponse(content=rss_no_date)]
    _FakeAsyncClientCM.fail_hosts = set()

    items, duplicates = await fetch_new_items(pool, settings, max_items=10)
    assert duplicates == 2
    assert [i.url for i in items] == ["http://example.com/d", "http://other.com/d"]
    assert items[0].published_at is not None
    assert items[1].published_at is None

    _FakeAsyncClientCM.responses = [FakeResponse(content=rss()), FakeResponse(content=rss(host="other.com"))]
    items, duplicates = await fetch_new_items(pool, settings, max_items=1)
    assert len(items) == 1
    assert duplicates == 2


async def test_fetch_new_items_drops_identical_duplicate_entries(monkeypatch) -> None:
    import app.feeds as feeds_mod

    monkeypatch.setattr(feeds_mod.httpx, "AsyncClient", _FakeAsyncClientCM)
    settings = make_settings()
    sources = [{"id": 1, "name": "S1", "feed_url": "http://example.com/rss", "language": "en"}]

    def router(method: str, sql: str, args: tuple[Any, ...]) -> Any:
        if "FROM sources" in sql:
            return sources
        return []

    item_xml = (
        f"<item><link>http://example.com/a</link><title>Article A</title><description>{BODY_A}</description></item>"
    )
    dup_rss = (
        '<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>' + item_xml + item_xml + "</channel></rss>"
    ).encode()
    _FakeAsyncClientCM.responses = [FakeResponse(content=dup_rss)]
    _FakeAsyncClientCM.fail_hosts = set()

    items, duplicates = await fetch_new_items(as_pool(FakePool(FakeConn(router))), settings, max_items=10)
    assert len(items) == 1
    assert duplicates == 0


async def test_fetch_new_items_skips_failing_feeds(monkeypatch) -> None:
    import app.feeds as feeds_mod

    monkeypatch.setattr(feeds_mod.httpx, "AsyncClient", _FakeAsyncClientCM)
    settings = make_settings()

    sources = [
        {"id": 1, "name": "S1", "feed_url": "http://example.com/rss", "language": "en"},
        {"id": 2, "name": "S2", "feed_url": "http://bad.com/feed", "language": "fr"},
    ]

    def router(method: str, sql: str, args: tuple[Any, ...]) -> Any:
        if "FROM sources" in sql:
            return sources
        return []

    pool = as_pool(FakePool(FakeConn(router)))
    _FakeAsyncClientCM.responses = [FakeResponse(content=rss())]
    _FakeAsyncClientCM.fail_hosts = {"bad.com"}

    items, duplicates = await fetch_new_items(pool, settings, max_items=10)
    assert len(items) == 2
    assert duplicates == 0
    _FakeAsyncClientCM.fail_hosts = set()
