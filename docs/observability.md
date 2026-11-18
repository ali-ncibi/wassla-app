# Observability & evals (local Phoenix, always on in docker)

The pipeline sends OpenInference/OTLP traces of the whole LangGraph agent workflow
(graph runs, per-node runs, every LLM call) to a local, self-hosted
[Arize Phoenix](https://phoenix.arize.com/) server, and runs offline evaluation
experiments against a golden dataset. Everything runs **in docker compose** —
there is no host-side mode.

## What runs

`make up` starts four services: `db`, `pipeline`, `web`, and `phoenix`
(UI + OTLP collector at http://localhost:6006, OTLP/HTTP on 6006, gRPC on 4317,
data persisted in the `phoenix_data` volume). Tracing is always on: `app/main.py`
calls `app.observability.setup_tracing()` before langchain/langgraph are imported,
which registers the OTLP tracer provider and the OpenInference LangChain instrumentor
(`openinference-instrumentation-langchain`). Custom `BaseChatModel` subclasses
(`providers/chat.py`) and the LangGraph nodes are traced automatically.

Per ingest run you get in the Phoenix UI:

- `POST /ingest/run` root span → `ingest` → `process_article` → `translate` /
  `categorize` / `summarize` / `evaluate` / `embed` / `persist` node spans → one
  `LLM` span per chat call
- LLM spans carry the `tag.tags = ["task:translate" | "task:categorize" | ...]` span
  tag and a `metadata.task` attribute (set in `graph/nodes.py:call_llm` via
  `using_tags`/`using_metadata`, which survive LangGraph's own per-node metadata)
- inputs/outputs (prompts, completions), model name, latency, token usage
  (prompt/completion/total — parsed from the API `usage` field), errors

## Run evals

```bash
make evals    # docker compose run --rm pipeline python -m evals.run_evals
```

`pipeline/evals/run_evals.py` (shipped in the pipeline image):

- loads golden examples from `pipeline/evals/dataset.jsonl`
  (one JSON object per line: `input.item` = a `FeedItem`, `output.expected_category`,
  `metadata.languages`)
- runs the article graph per example **without the persist node**
  (`build_article_graph(deps, persist=False)`), so no DB writes
- scores each run with evaluators:
  - **structural (always, free, work with `LLM_PROVIDER=stub`)**: all target languages
    present in translations+summaries, summary length bound, evaluation score shape
  - **LLM-behavior (real provider only)**: exact category match, Arabic-script check on
    the `ar` translation, and an LLM-as-judge reusing the pipeline's own
    `EVALUATION TASK` rubric (`graph/prompts.py:evaluate_messages`)
- creates/reuses the Phoenix dataset `wassla-article-evals` and runs a versioned
  Phoenix **experiment**; eval task runs are traced too (tag `eval`)

Evaluator parameters are bound by name (Phoenix convention): `output` = task output,
`input` / `metadata` / `expected` = dataset example fields.

Add examples by appending lines to `evals/dataset.jsonl`, or from the Phoenix UI by
adding interesting production spans to a dataset.

## Daily workflow

1. `make up` — everything including Phoenix comes up; tracing is on.
2. Use the app normally (web UI at http://localhost:3000, or the 15-min cron ingest).
3. Open http://localhost:6006 → project `wassla-pipeline` (name from
   `PHOENIX_PROJECT_NAME` in `.env`):
   - browse traces, click a span for full prompt/completion, latency, tokens, errors
     (red spans)
   - filter by tag: `tag.tags contains "task:evaluate"`, `"ingest"`, `"article"`, `"eval"`
   - sort spans by `llm.token_count.total` or duration for cost/latency hotspots
4. Before/after changing a prompt or model (`graph/prompts.py`, `MODEL_*` in `.env`),
   run `make evals` and compare experiments side by side in
   **Datasets → wassla-article-evals → Experiments** — per-example scores show exactly
   which article regressed.

## Dependencies

All in the pipeline image (main `dependencies` in `pipeline/pyproject.toml`, hash-pinned
in `requirements.txt` via `uv pip compile --generate-hashes`):
`arize-phoenix-otel`, `openinference-instrumentation-langchain`, `opentelemetry-sdk`,
`arize-phoenix` (client + experiments), `pandas`.

Regenerate the lockfile after changing deps:

```bash
cd pipeline && uv lock && uv pip compile pyproject.toml -o requirements.txt --python-version 3.12 --generate-hashes
```
