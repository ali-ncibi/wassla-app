import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("LLM_PROVIDER", "stub")
os.environ.setdefault("EMBEDDING_PROVIDER", "stub")
os.environ.setdefault("INGEST_TOKEN", "test-token")
os.environ.setdefault("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces")
os.environ.setdefault("PHOENIX_PROJECT_NAME", "wassla-tests")

import asyncio
from collections.abc import Callable
from typing import Any, cast

import asyncpg
import pytest

from app.config import Settings
from app.graph.nodes import Deps
from app.providers.chat import StubChatModel
from app.providers.embeddings import StubEmbeddings

DEFAULT = object()


def make_settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "_env_file": None,
        "database_url": "postgresql://test:test@localhost:5432/test",
        "llm_provider": "mistral",
        "embedding_provider": "mistral",
        "ingest_token": "",
    }
    base.update(overrides)
    return Settings(**base)


class FakeTransaction:
    def __init__(self) -> None:
        self.entered = False

    async def __aenter__(self) -> "FakeTransaction":
        self.entered = True
        return self

    async def __aexit__(self, *args: Any) -> bool:
        return False


class FakeConn:
    """Records every call and answers from a router: (method, sql, args) -> value."""

    def __init__(self, router: Callable[[str, str, tuple[Any, ...]], Any] | None = None) -> None:
        self.calls: list[tuple[str, str, tuple[Any, ...]]] = []
        self.router = router
        self.transactions: list[FakeTransaction] = []

    def _result(self, method: str, sql: str, args: tuple[Any, ...], default: Any) -> Any:
        self.calls.append((method, sql, args))
        if self.router is None:
            return default
        value = self.router(method, sql, args)
        return default if value is DEFAULT else value

    async def fetch(self, sql: str, *args: Any) -> list[Any]:
        return self._result("fetch", sql, args, [])

    async def fetchrow(self, sql: str, *args: Any) -> Any:
        return self._result("fetchrow", sql, args, None)

    async def fetchval(self, sql: str, *args: Any) -> Any:
        return self._result("fetchval", sql, args, None)

    async def execute(self, sql: str, *args: Any) -> Any:
        return self._result("execute", sql, args, None)

    def transaction(self) -> FakeTransaction:
        txn = FakeTransaction()
        self.transactions.append(txn)
        return txn


class FakeAcquire:
    def __init__(self, conn: FakeConn) -> None:
        self.conn = conn

    async def __aenter__(self) -> FakeConn:
        return self.conn

    async def __aexit__(self, *args: Any) -> bool:
        return False


class FakePool:
    def __init__(self, conn: FakeConn | None = None) -> None:
        self.conn = conn or FakeConn()
        self.closed = False

    def acquire(self) -> FakeAcquire:
        return FakeAcquire(self.conn)

    async def close(self) -> None:
        self.closed = True


def as_pool(pool: FakePool) -> asyncpg.Pool:
    """Cast a FakePool to asyncpg.Pool for call sites typed against the real pool."""
    return cast("asyncpg.Pool", pool)


def make_deps(
    settings: Settings | None = None,
    pool: FakePool | None = None,
    chat: dict[str, Any] | None = None,
    embedder: Any = None,
) -> Deps:
    s = settings or make_settings()
    if chat is None:
        chat = {task: StubChatModel() for task in ("translate", "categorize", "summarize", "evaluate")}
    return Deps(
        settings=s,
        pool=as_pool(pool or FakePool()),
        chat=chat,
        embedder=embedder if embedder is not None else StubEmbeddings(dim=s.embedding_dim),
        semaphore=asyncio.Semaphore(4),
    )


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def deps() -> Deps:
    return make_deps()
