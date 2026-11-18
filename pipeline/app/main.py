import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .observability import setup_tracing

setup_tracing(get_settings())

from .db import create_pool
from .graph.nodes import Deps
from .providers import build_chat_models, build_embeddings
from .routes import articles, ingest, meta, search


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    pool = await create_pool(settings)
    deps = Deps(
        settings=settings,
        pool=pool,
        chat=build_chat_models(settings),
        embedder=build_embeddings(settings),
        semaphore=asyncio.Semaphore(settings.llm_max_concurrency),
    )
    app.state.deps = deps
    yield
    await pool.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Wassla Pipeline", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(ingest.router)
    app.include_router(articles.router)
    app.include_router(search.router)
    app.include_router(meta.router)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"service": settings.app_name, "docs": "/docs"}

    return app


app = create_app()
