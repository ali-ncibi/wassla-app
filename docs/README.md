# Wassla — Documentation Index

Short, current docs for the codebase. Start at the root [README.md](../README.md).

| File | Contents |
|---|---|
| [quickstart.md](quickstart.md) | Setup, `make up`, manual ingest, stub mode, all `make` commands |
| [architecture.md](architecture.md) | Mermaid diagrams: components, ingest sequence, agent graph, RAG flow, tracing |
| [db.md](db.md) | PostgreSQL image (pgvector / pg_cron / pg_net), schema, 18 seed sources, cron job |
| [pipeline.md](pipeline.md) | FastAPI service: env config, providers, LangGraph agents, RAG, REST API, tracing hook |
| [web.md](web.md) | Nuxt 4 frontend: pages, read-only `/api/*` proxy, i18n |
| [testing.md](testing.md) | `make check` / `make fix`: ruff, mypy/pyright, ESLint/vue-tsc, pytest + vitest with 100% coverage |
| [observability.md](observability.md) | Phoenix tracing (always on in compose) + eval experiments via `make evals` |
