.PHONY: setup lint fix typecheck check test test-pipeline test-web evals lint-pipeline lint-fix-pipeline lint-web lint-fix-web typecheck-pipeline typecheck-web up down

setup:
	cd pipeline && uv sync --all-groups
	cd web && pnpm install

lint-pipeline:
	cd pipeline && uv run --group dev ruff format --check app && uv run --group dev ruff check app

lint-fix-pipeline:
	cd pipeline && uv run --group dev ruff check --fix app && uv run --group dev ruff format app

typecheck-pipeline:
	cd pipeline && uv run --group dev mypy && uv run --group dev pyright app tests

test-pipeline:
	cd pipeline && uv run --group test pytest

lint-web:
	cd web && pnpm lint

lint-fix-web:
	cd web && pnpm lint:fix

typecheck-web:
	cd web && pnpm typecheck

test-web:
	cd web && pnpm test

lint: lint-pipeline lint-web

fix: lint-fix-pipeline lint-fix-web

typecheck: typecheck-pipeline typecheck-web

test: test-pipeline test-web

check: lint fix typecheck test

evals:
	docker compose run --rm pipeline python -m evals.run_evals

up:
	docker compose up -d --build

down:
	docker compose down
