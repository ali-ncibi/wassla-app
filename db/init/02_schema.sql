CREATE TABLE IF NOT EXISTS sources (
    id            SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    feed_url      TEXT NOT NULL UNIQUE,
    language      TEXT NOT NULL DEFAULT 'en',
    active        BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS articles (
    id              BIGSERIAL PRIMARY KEY,
    source_id       INTEGER NOT NULL REFERENCES sources(id),
    url             TEXT NOT NULL UNIQUE,
    guid            TEXT,
    source_language TEXT NOT NULL,
    title           TEXT NOT NULL,
    body            TEXT NOT NULL,
    summary         TEXT,
    category        TEXT,
    eval_score      REAL,
    eval_verdict    TEXT,
    eval_feedback   TEXT,
    status          TEXT NOT NULL DEFAULT 'processed',
    published_at    TIMESTAMPTZ,
    scraped_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS article_translations (
    article_id  BIGINT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    lang        TEXT NOT NULL,
    title       TEXT NOT NULL,
    body        TEXT NOT NULL,
    summary     TEXT,
    embedding   vector(1024),
    PRIMARY KEY (article_id, lang)
);

CREATE INDEX IF NOT EXISTS idx_articles_category   ON articles (category);
CREATE INDEX IF NOT EXISTS idx_articles_published  ON articles (COALESCE(published_at, scraped_at) DESC);
CREATE INDEX IF NOT EXISTS idx_translations_embedding ON article_translations USING hnsw (embedding vector_cosine_ops);
