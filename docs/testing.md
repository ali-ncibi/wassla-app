# Testing & lint

`make check` runs everything; `make fix` auto-fixes lint issues.

| Target | What |
|---|---|
| `make lint-pipeline` / `lint-pipeline-fix` | `ruff format --check` + `ruff check` on `pipeline/app` / `--fix` + format |
| `make lint-web` / `lint-web-fix` | `eslint .` / `eslint . --fix` in `web` |
| `make typecheck-pipeline` | strict mypy + pyright (`app`, `tests`) |
| `make typecheck-web` | `nuxi typecheck` (vue-tsc) |
| `make test-pipeline` | `pytest` with `--cov=app`, 100% coverage enforced |
| `make test-web` | `vitest run --coverage`, 100% statements/branches/functions/lines enforced |

## Pipeline tests (`pipeline/tests/`)

One module per app module (`test_nodes.py`, `test_pipeline.py`, `test_routes.py`,
`test_providers.py`, `test_observability.py`, ...). DB is faked (`FakePool`/`FakeConn`
in `conftest.py`), LLMs are `StubChatModel`/`FakeChat`, so the whole graph runs
offline. Tracing spans from tests go to the separate `wassla-tests` Phoenix project
(or fail fast if Phoenix is down).

## Web tests (`web/tests/`)

Vitest + @vue/test-utils + happy-dom. Nuxt auto-imports are mocked (`tests/setup.ts`);
pages are mounted through a `Suspense` wrapper. Coverage thresholds are 100% across
`app/` + `server/`.

## Evals

Not part of `make check` (they call real LLMs): `make evals` runs
`pipeline/evals/run_evals.py` in the pipeline container against Phoenix — see
[observability.md](observability.md).
