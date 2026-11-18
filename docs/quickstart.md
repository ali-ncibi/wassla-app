# Quickstart

## Setup

```bash
cp .env.example .env
# edit .env: MISTRAL_API_KEY (or OPENAI_API_KEY), INGEST_TOKEN=$(openssl rand -hex 32)
make setup        # uv sync (pipeline) + pnpm install (web)
```

## Run

```bash
make up           # docker compose up -d --build → db, pipeline, web, phoenix
```

- Web UI: http://localhost:3000 (en/fr/ar) · API docs: http://localhost:8000/docs · Phoenix: http://localhost:6006
- Health: `curl http://localhost:8000/health`
- Ingest runs every 15 min automatically (pg_cron job → pg_net POST to the pipeline). Manual:

```bash
curl -X POST http://localhost:8000/ingest/run \
  -H "X-Ingest-Token: $INGEST_TOKEN" -H 'Content-Type: application/json' \
  -d '{"max_items": 50}'
```

- No API keys? `LLM_PROVIDER=stub`, `EMBEDDING_PROVIDER=stub` in `.env`, then `make up` — full deterministic run.

## Daily commands

| Command | What |
|---|---|
| `make check` | lint + typecheck + tests (pipeline: ruff, mypy, pyright, pytest @100% cov; web: ESLint, vue-tsc, vitest @100% cov) |
| `make fix` | auto-fix lint (ruff --fix + format; eslint --fix) |
| `make test` / `make lint` / `make typecheck` | subsets of check |
| `make evals` | run eval experiments in the pipeline container, results in Phoenix |
| `make up` / `make down` | start / stop the whole compose stack |

Local dev without docker: `cd pipeline && uv run --group dev uvicorn app.main:app` (needs `DATABASE_URL` pointing at a reachable Postgres, e.g. the published `127.0.0.1:5432`), and `cd web && pnpm dev` with `NUXT_API_BASE=http://localhost:8000`.
