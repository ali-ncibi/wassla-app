# Web service

Nuxt 4 (Vue 3.5) SSR app on :3000, Tailwind CSS 4, Nitro node-server. Trilingual
(en/fr/ar) via `app/utils/i18n.ts` + `app/composables/useLang.ts` (lang in the
`?lang=` query param).

## Pages (`app/pages/`)

- `index.vue` — article list with category chips and URL-driven pagination (`?page=&category=` → `limit`/`offset`)
- `article/[id].vue` — full article in the selected language
- `search.vue` — RAG search box: hits + grounded cited answer
- `stats.vue` — pipeline stats dashboard

Components (`app/components/`): `SiteHeader`, `LangSwitcher`, `ArticleCard`,
`CategoryChips`, `Pagination`.

## API proxy

`server/api/[...].ts` forwards requests to the pipeline (`NUXT_API_BASE`,
`http://pipeline:8000` in compose) **read-only**: only GET/HEAD are proxied;
`/ingest/*` is blocked, so the ingest token never reaches the browser.

## Checks

`make lint-web` (ESLint incl. vue rules), `make lint-web-fix`, `make typecheck-web`
(vue-tsc), `make test-web` (vitest + 100% coverage enforced). See
[testing.md](testing.md).
