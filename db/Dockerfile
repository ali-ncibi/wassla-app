FROM pgvector/pgvector:pg16

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-16-cron \
        postgresql-server-dev-16 \
        build-essential \
        git \
        ca-certificates \
        libcurl4-openssl-dev \
    && git clone --depth 1 --branch v0.20.4 https://github.com/supabase/pg_net.git /tmp/pg_net \
    && make -C /tmp/pg_net \
    && make -C /tmp/pg_net install \
    && apt-get purge -y build-essential git \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* /tmp/pg_net
