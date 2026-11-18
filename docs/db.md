# Database

`db/Dockerfile` builds PostgreSQL 16 with `pgvector`, `pg_cron`, `pg_net`.
Init scripts in `db/init/` run on first boot (volume `pgdata`):

- `01_extensions.sql` — `vector`, `pg_cron`, `pg_net`
- `02_schema.sql` — tables:
  - `sources(id, name, feed_url UNIQUE, language, active)`
  - `articles(id, source_id, url UNIQUE, guid, source_language, title, body, summary, category, eval_score, eval_verdict, eval_feedback, status, published_at, scraped_at)`
  - `article_translations(article_id, lang, title, body, summary, embedding vector(1024), PRIMARY KEY(article_id, lang))` + HNSW cosine index on `embedding`
- `03_seed.sql` — 18 RSS sources (en/fr/ar) and the cron job:

```sql
SELECT cron.schedule('wassla-ingest', '*/15 * * * *', $$
  SELECT net.http_post(url := 'http://pipeline:8000/ingest/run',
    headers := jsonb_build_object('X-Ingest-Token', current_setting('app.ingest_token')));
$$);
```

The ingest token is injected into Postgres at container start
(`-c app.ingest_token=${INGEST_TOKEN}` in compose), so the cron job can call the
token-protected endpoint inside the compose network.

Connect: `psql postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:5432/$POSTGRES_DB`
