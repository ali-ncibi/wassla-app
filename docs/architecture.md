# Architecture

## Components

```mermaid
flowchart LR
    subgraph Browser
        U[User]
    end

    subgraph Compose["docker compose: wassla"]
        direction TB
        WEB["web (Nuxt 4 :3000)<br/>SSR pages + read-only /api/* proxy"]
        PIPE["pipeline (FastAPI :8000)<br/>/ingest/run · /articles · /search · /stats · /health"]
        DB[("db (Postgres 16 + pgvector<br/>+ pg_cron + pg_net :5432)")]
        PHO["phoenix (:6006)<br/>traces + eval datasets/experiments"]
    end

    RSS[(RSS feeds<br/>18 sources en/fr/ar)]
    LLM[(LLM APIs<br/>Mistral / OpenAI-compatible<br/>chat + embeddings)]

    U -->|HTTP| WEB
    WEB -->|"GET/HEAD only"| PIPE
    PIPE -->|asyncpg| DB
    DB -->|rows| PIPE
    PIPE -->|httpx RSS| RSS
    RSS -->|feed XML| PIPE
    PIPE -->|"chat/completions, /embeddings"| LLM
    LLM -->|responses + usage| PIPE
    PIPE -->|"OTLP spans (always on)"| PHO
```

## Ingest sequence

```mermaid
sequenceDiagram
    autonumber
    participant CRON as pg_cron, every 15 min
    participant PIPE as pipeline on :8000
    participant DB as db, postgres
    participant RSS as RSS feeds, 18 sources
    participant LLM as LLM and embeddings API

    CRON->>PIPE: POST /ingest/run + X-Ingest-Token
    PIPE->>DB: SELECT active sources
    DB-->>PIPE: sources (id, feed_url, language)
    PIPE->>DB: SELECT known article urls
    DB-->>PIPE: urls
    PIPE->>RSS: GET every feed (5 MB cap, redirects only to known source hosts)
    RSS-->>PIPE: feed XML entries
    PIPE->>PIPE: drop duplicates, sort by published_at desc, cap at max_items
    loop per fresh article — Send fan-out, at most LLM_MAX_CONCURRENCY at once
        PIPE->>LLM: translate per target lang (json_mode)
        LLM-->>PIPE: {title, body} JSON
        PIPE->>LLM: categorize (json_mode)
        LLM-->>PIPE: {category, confidence} JSON
        PIPE->>LLM: summarize per lang
        LLM-->>PIPE: summary text
        PIPE->>LLM: evaluate (json_mode, independent QA judge)
        LLM-->>PIPE: {score 0-10, verdict, issues} JSON
        PIPE->>LLM: embed translations per lang
        LLM-->>PIPE: vectors
        PIPE->>DB: INSERT article + translations + embeddings
        DB-->>PIPE: article_id
    end
    PIPE-->>CRON: 200 IngestResponse {fetched, duplicates_skipped, processed, failed, duration_ms, articles, errors}
```

## Per-article agent graph

One LangGraph subgraph invocation per article — a strict linear chain
(`graph/pipeline.py:build_article_graph`; `evaluate` only scores, it does not
branch — a low score is stored as status `needs_review`):

```mermaid
flowchart LR
    START([FeedItem]) --> T["translate<br/>per target lang<br/>(json_mode)"]
    T --> C["categorize<br/>(json_mode)"]
    C --> S["summarize<br/>per lang"]
    S --> E["evaluate<br/>QA score 0-10<br/>(json_mode)"]
    E --> V["embed<br/>per lang"]
    V --> P[("persist<br/>articles +<br/>article_translations")]
    P --> END([article_id])
```

## RAG search

```mermaid
flowchart LR
    Q(["GET /search?q=...&lang=..."]) --> V["embed query"]
    V --> DB[("pgvector cosine search<br/>top_k, min_score filter")]
    DB --> H["hits (title, summary, url, score)"]
    H --> A{"RAG_ANSWER_ENABLED<br/>and hits found?"}
    A -->|yes| L["LLM answer over hits<br/>cited as [1], [2], ...<br/>in requested lang"]
    A -->|no| R(["SearchResponse:<br/>answer + hits"])
    L --> R
```

## Tracing

The pipeline instruments LangChain/LangGraph via OpenInference at startup
(`app/observability.py`, called first in `app/main.py`) and exports OTLP spans to
Phoenix. Every HTTP request becomes a trace: `POST /ingest/run → ingest →
process_article → LangGraph → translate/... → LLM` with per-span latency, model,
token usage, and tags (`ingest`, `article`, `eval`, `task:<name>`). See
[observability.md](observability.md).
