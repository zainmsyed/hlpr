FROM postgres:17

# Install pgvector extension
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-17-pgvector && \
    rm -rf /var/lib/apt/lists/*

COPY init-vector.sql /docker-entrypoint-initdb.d/
RUN chmod 644 /docker-entrypoint-initdb.d/init-vector.sql