# Pipeline service

FastAPI app (`pipeline/app/`), runs in docker on :8000, always traces to Phoenix.

## Layout

```
app/
├── main.py            # create_app(); calls observability.setup_tracing() before langchain imports
├── config.py          # Settings (pydantic-settings, all from .env)
├── observability.py   # OTel/OpenInference setup → Phoenix (phoenix:6006)
├── db.py              # asyncpg pool
├── feeds.py           # RSS fetch (size/redirect caps, host allowlist), FeedItem
├── repo.py            # SQL: insert_article, list/get articles, vector search
├── rag.py             # embed query → search → optional cited LLM answer
├── schemas.py         # pydantic request/response models
├── providers/         # chat + embeddings: mistral | openai-compatible | stub
└── graph/
    ├── pipeline.py    # build_pipeline_graph / build_article_graph(persist=True)
    ├── nodes.py       # fetch, process_article, translate, categorize, summarize,
                       # evaluate, embed, persist; call_llm() tags spans task:<name>
    ├── prompts.py     # all system prompts (UNTRUSTED_GUARD against prompt injection)
    └── state.py       # TypedDict states
evals/                 # run_evals.py + dataset.jsonl (make evals, runs in docker)
```

## Config

All settings are env vars (`.env`, see `.env.example`): `DATABASE_URL`,
`LLM_PROVIDER`/`EMBEDDING_PROVIDER` (`mistral` | `openai` | `stub`), API keys and
base URLs, `MODEL_TRANSLATE/CATEGORIZE/SUMMARIZE/EVALUATOR/OPENAI`, `LLM_TEMPERATURE`,
`LLM_TIMEOUT_SECONDS`, `LLM_MAX_CONCURRENCY`, `LANGUAGES`, `CATEGORIES`,
`INGEST_TOKEN`, `INGEST_MAX_ITEMS`, `EVAL_MIN_SCORE`, feed caps, `RAG_TOP_K`,
`RAG_MIN_SCORE`, `RAG_ANSWER_ENABLED`, `CORS_ORIGINS`, `PHOENIX_PROJECT_NAME`.

## REST API

| Endpoint | Notes |
|---|---|
| `POST /ingest/run` | body `{max_items?}`; requires `X-Ingest-Token` header |
| `GET /articles` | filters: `lang`, `category`, `limit`, `offset` |
| `GET /articles/{id}` | `?lang=` |
| `GET /search` | `q`, `lang`, `top_k?` → hits + optional cited `answer` |
| `GET /stats` | totals, per-category/lang counts, avg eval score, last ingest |
| `GET /categories`, `GET /config` | metadata |
| `GET /health` | status + resolved providers/models |

## Providers

`build_chat_model(settings, task)` picks per-task models (translate/categorize/
summarize/evaluate). Real providers go through a custom
`OpenAICompatibleChatModel` (plain httpx to `/chat/completions`, `json_mode` for
structured tasks, `usage_metadata` parsed into spans for token counts).
`stub` providers make the whole graph deterministic without API keys.

## Tracing

`main.py` calls `setup_tracing()` before importing langgraph, registering OTLP →
Phoenix. LLM calls are tagged `task:<name>`; graphs `ingest` / `article` / `eval`.
See [observability.md](observability.md).
