# PostgreSQL Migration Guide

Steps to upgrade Autergo from SQLite (default) to PostgreSQL. The project is already 95% Postgres-ready — this guide finishes the last 5% and runs the switch.

## Why PostgreSQL

- Concurrent writes (SQLite locks the whole DB on writes; real interviews have multiple HRs + candidates)
- Native `JSONB` for the encrypted state columns (faster + indexable)
- Full-text search for RAG/audit log queries
- Alembic-friendly — proper transactional DDL
- Required for any multi-pod deployment

## What's already in place (no work needed)

- `asyncpg==0.29.0` is pinned in `requirements.txt`
- `docker-compose.yml` already declares the `db` service (postgres:15-alpine, with healthcheck)
- `alembic/env.py` is already async-aware and imports all models
- `config.py` has `DATABASE_URL` (env-driven) + `DB_SSL_MODE` setting
- `ci.yml` has a `backend-postgres` job that runs against a real Postgres service container

## Steps to perform

### 1. Pick a Postgres version

Pin to `postgres:16-alpine` (current LTS-ish; supported until Nov 2028). Bump from 15 in `docker-compose.yml`:

```yaml
db:
  image: postgres:16-alpine
```

### 2. Set the connection string

In `Vedrix/backend/.env`:

```dotenv
# Local dev (docker-compose)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/vedrix

# Production
DATABASE_URL=postgresql+asyncpg://USER:PASS@HOST:5432/vedrix_prod
DB_SSL_MODE=require
```

For local SQLite-only test runs, keep `DATABASE_URL=sqlite+aiosqlite:///./vedrix.db` as a fallback.

### 3. Add connection-pool tuning to `app/db/session.py`

SQLite is fine without pooling; Postgres needs it. Add to the `create_async_engine` call:

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,        # detect dead connections (PgBouncer / RDS)
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,         # 30 min — important for cloud DBs
    echo=False,
)
```

### 4. Fix FK cycles (Postgres is strict; SQLite was lenient)

The CI warnings already show this:

```
SAWarning: Can't sort tables for DROP; ... unresolvable foreign key dependency
exists between tables: interview_plan, interview_session
```

Fix in `app/models/interview_plan.py` and `app/models/interview.py` — mark the FKs in the cycle with `use_alter=True`:

```python
session_id: int = Field(
    foreign_key="interview_session.id",
    sa_column_kwargs={"use_alter": True, "name": "fk_interview_plan_session"},
)
```

Apply the same pattern anywhere a model has two FKs between the same two tables.

### 5. Generate the first Alembic migration

After the model pool fix:

```bash
cd Vedrix/backend
alembic revision --autogenerate -m "initial_postgres_schema"
alembic upgrade head
```

Review the generated file — autogenerate misses:
- `EncryptedJSON` custom types (verify the column type)
- Indexes declared via `Index(...)` (verify they're created)
- Enum types (SQLAlchemy doesn't autogenerate CREATE TYPE)

### 6. Migrate existing data (only if you have prod data)

Skip this if you're starting fresh.

```bash
# Export from SQLite
sqlite3 vedrix.db .dump > dump.sql
# (or use a Python script with pandas/SQLAlchemy core for cleaner export)

# Import to Postgres — easiest with pgloader:
pgloader sqlite:///vedrix.db postgresql://postgres:postgres@localhost/vedrix
```

Then verify row counts and run sanity queries against each table.

### 7. Update tests to run against Postgres (optional but recommended)

The new `backend-postgres` CI job already does this. To run locally:

```bash
docker compose up -d db
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/vedrix_test \
  pytest
```

For fast unit tests that don't need a DB, keep the existing SQLite test path — just override `DATABASE_URL` in `conftest.py`.

### 8. Production cutover checklist

- [ ] Postgres instance provisioned (managed: RDS / Cloud SQL / Supabase / Neon)
- [ ] DATABASE_URL + DB_SSL_MODE set in deployment env
- [ ] Connection pool sized for expected concurrency (start: `pool_size=10, max_overflow=20`)
- [ ] `alembic upgrade head` run as a one-shot job (the new `db-migrate` job in `cd.yml` does this)
- [ ] Backups enabled (PITR or daily snapshots)
- [ ] Monitoring: pgbouncer/exporter for `pg_stat_activity`, slow query log
- [ ] Smoke test: `GET /health` returns 200, login works, one interview can be started
- [ ] Old SQLite backup kept for 30 days (just in case)

### 9. Roll back if it goes wrong

Postgres is the new source of truth, but the SQLite file is still in `Vedrix/backend/vedrix.db`. If something explodes within 24h:

1. Revert the env var to the SQLite URL
2. `git revert` the cutover commit
3. Redeploy

## Files this guide will touch

- `Vedrix/docker-compose.yml` — bump postgres 15 → 16
- `Vedrix/backend/app/db/session.py` — add pool tuning
- `Vedrix/backend/app/models/interview_plan.py` — `use_alter=True` on cyclic FK
- `Vedrix/backend/alembic/versions/XXXX_initial_postgres_schema.py` — new
- `Vedrix/backend/.env.example` — document both DATABASE_URL formats
- `Vedrix/backend/requirements.txt` — already has `asyncpg`, no change

## Verification commands

```bash
# Confirm asyncpg can talk to Postgres
python -c "import asyncpg; print('asyncpg', asyncpg.__version__)"

# Confirm models import without errors (catches mapper init bugs)
python -c "from app.models import *; print('OK')"

# Confirm Alembic sees all tables
alembic check

# Confirm Alembic migrations apply cleanly to a fresh DB
alembic upgrade head && alembic downgrade base && alembic upgrade head
```
