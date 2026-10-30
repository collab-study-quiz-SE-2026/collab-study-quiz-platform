# Collaborative Study Material & Quiz Platform (CSMQP)

A web platform where students share study material, contribute to a
collaborative question bank, play synchronized live quizzes, and track their
performance over time.

> Software Engineering Mini-Project, 2026

## Overview

CSMQP is a distributed full-stack web application for higher-education
learning environments. It supports:

- Peer-to-peer study material sharing (upload, tag, search, download)
- Collaborative question bank curation and moderation
- Synchronized live quiz rooms and self-paced practice quizzes
- Longitudinal performance analytics with topic-level feedback

## Architecture (summary)

Layered 3-tier architecture with an event-driven subsystem for real-time quizzes.

| Tier | Technology |
|---|---|
| Presentation | React SPA, Tailwind CSS, Recharts/Chart.js, WebSocket client |
| Application | REST API + WebSocket quiz engine (Node.js / FastAPI), Nginx reverse proxy |
| Data & Storage | PostgreSQL 15, S3-compatible object storage |

Security highlights: TLS 1.3, JWT (HTTP-only cookies), Bcrypt password hashing,
RBAC, parameterized queries, server-side answer-key withholding.

## Repository Structure

```
collab-study-quiz-platform/
├── README.md
├── .gitignore
├── docs/                   # Existing SRS, SDD, and test plan PDFs
└── backend/
    ├── app/
    │   ├── __init__.py
    │   ├── database.py
    │   └── main.py
    ├── tests/
    │   ├── test_health.py
    │   ├── test_database.py
    │   └── test_sqlalchemy.py
    ├── alembic/
    │   ├── env.py
    │   ├── script.py.mako
    │   └── versions/
    ├── alembic.ini
    └── requirements.txt
```

## Day 1: Run the backend on Windows

Install Python 3.12 or newer. Open PowerShell in the repository folder.
The commands below use the virtual environment directly; activation and
PowerShell execution-policy changes are not needed.

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

If `py` is unavailable, use `python -m venv .venv` instead, after checking
`python --version` reports Python 3.12 or newer.

Open http://127.0.0.1:8000/health in your browser. Expected response:

```json
{"status":"ok"}
```

To check from another PowerShell window, run:

```powershell
curl.exe -i http://127.0.0.1:8000/health
```

Expect HTTP status `200 OK`. Stop the server with `Ctrl+C`.
From the `backend` folder, run the automated test:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The test checks that `/health` returns status 200 and exactly `{"status":"ok"}`.
It runs in memory, so the server does not need to be running.

### How the small backend works

- `app/__init__.py` is empty and marks `app` as a Python package.
- `app/main.py` imports `FastAPI` and creates the application with `app = FastAPI()`.
  The decorator `@app.get("/health")` connects GET requests on `/health` to
  `health()`. The function returns a Python dictionary, which FastAPI sends as
  JSON with status 200.
- Uvicorn is the web server. `app.main:app` tells it to import the `app` object
  from `app/main.py`. `--reload` restarts the server when you save code changes.
- `tests/test_health.py` imports `TestClient` and our application. Pytest finds
  the function because its name begins with `test_`. `with TestClient(app)`
  creates a test client and cleans it up afterward. `client.get("/health")`
  makes a request; the two `assert` lines check the status and parsed JSON.
- `requirements.txt` lists FastAPI (API), Uvicorn (server), Pytest (tests), and
  HTTPX (used by the test client). Pip also installs their required dependencies.
- `.gitignore` keeps virtual environments, Python caches, and local secret files
  out of Git. The `.venv` folder is local; each teammate creates their own.

This is the Day 1 subset of [Story #21](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/21)
under [Epic #20](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/20).
The initial backend implements `/health`. FastAPI also provides its default
API documentation at `/docs`.
The existing test plan's TC-11 uses `/healthz` for a future availability test;
this exercise uses `/health` and does not implement that soak test.
Authentication and the other planned features remain separate work.
Story #21 is not complete with this setup alone.

## Day 1 continued: Local PostgreSQL

Tracked in [Task #32](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/32),
part of Story #21. This work is separate from initial backend PR #31.

### 1. Start Docker Desktop

Open **Docker Desktop** from the Windows Start menu and wait until the engine
is running. Use Linux containers with the WSL 2 backend (Settings > General).
Docker is already installed; do not reinstall it. In PowerShell, check:

```powershell
docker --version
docker compose version
docker info
```

### 2. Configure your local environment

From the repository root, copy the example **once**:

```powershell
Copy-Item .env.example .env
notepad .env
```

Replace `PGPASSWORD` with your own local development password. Leave the host
as `127.0.0.1`, port as `5432`, and database as `csmqp_dev`. Keep values unquoted
and without spaces for the simple loader below. Never commit `.env`.
Do not overwrite an existing `.env` when repeating these instructions.

Compose reads `.env` automatically. FastAPI does not, so load these values into
the PowerShell window where you will run the backend:

```powershell
Get-Content .env | ForEach-Object {
    if ($_ -match '^PG[A-Z]+=') {
        $parts = $_ -split '=', 2
        [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
    }
}
```

### 3. Start and check PostgreSQL

From the repository root:

```powershell
docker compose config --quiet
docker compose up -d db
docker compose ps
docker compose exec db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;"'
```

`config --quiet` validates the configuration without printing the resolved
password. Wait for `db` to become healthy. Expect `accepting connections` and
a single row containing `1`. Compose creates the development database on the
first start. Credentials initialize a new volume only; changing `.env` later
does not change an existing database's password. Port 5432 must be available.

### 4. Run FastAPI and check both endpoints

In the PowerShell window where you loaded `.env`:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Create `.venv` using the earlier instructions if it does not exist.
In another PowerShell window:

```powershell
curl.exe -i http://127.0.0.1:8000/health
curl.exe -i http://127.0.0.1:8000/health/db
```

Both should return HTTP 200. Their bodies are `{"status":"ok"}` and
`{"status":"ok","database":"connected"}`. If PostgreSQL is unavailable,
`/health/db` returns HTTP 503 with `{"detail":"Database unavailable"}`.
The original `/health` does not require a database connection.

### 5. Run tests against a dedicated database

From the repository root, create the separate test database **once**:

```powershell
docker compose exec db sh -c 'createdb -U "$POSTGRES_USER" csmqp_test'
```

If it already exists, reuse it. In a PowerShell window, load `.env` using the
loader above, then run:

```powershell
$env:TEST_PGDATABASE = 'csmqp_test'
cd backend
.\.venv\Scripts\python.exe -m pytest
```

All four tests should pass. The original test is preserved. The live database
test temporarily selects `TEST_PGDATABASE` and only runs `SELECT 1`; it does not
create tables or change development data. It refuses to use the configured
development database. Without `TEST_PGDATABASE`, both live database tests are
skipped; the original health and failure-response tests still run.
The failure test simulates a connection error and
checks HTTP 503 and the generic response, so private error details stay hidden.

### 6. Stop safely

Stop FastAPI with `Ctrl+C`. From the repository root:

```powershell
docker compose stop db
```

The named volume preserves both databases. Start again with
`docker compose up -d db`. Never use `docker compose down -v` or delete the volume.

### What the new code and files do

- `docker-compose.yml` runs only `postgres:15` as `db`. `environment` maps the
  local `PG*` settings to the image's `POSTGRES_*` settings. `ports` makes it
  available only on this computer. `postgres_data` stores its data persistently.
  `pg_isready` checks readiness; `$$` lets the container expand its own variables.
- `.env.example` provides safe placeholders. `.env` holds your local values and
  is ignored; `.gitignore` explicitly allows the example to be committed.
- `psycopg[binary]` is the PostgreSQL driver with a prebuilt library, so Windows
  does not need a compiler or separate PostgreSQL client installation.
- In `app/main.py`, `@app.get("/health/db")` registers the new route.
  `psycopg.connect(connect_timeout=3)` uses `PGHOST`, `PGPORT`, `PGDATABASE`,
  `PGUSER`, and `PGPASSWORD` from the backend process's environment, with a
  three-second connection timeout. The nested `with` blocks close the cursor
  and connection even when an error occurs. `execute("SELECT 1")` sends the
  query and `fetchone()` reads its row. `except psycopg.Error` catches database
  failures and raises a generic HTTP 503. A successful query returns the
  connected JSON response.
- `tests/test_database.py` adds the live connectivity test and the simulated
  failure test. Pytest's `monkeypatch` restores environment/function changes
  after each test. No ORM, application tables, or migrations are involved.

## SQLAlchemy and Alembic foundation

Tracked in [Task #34](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/34),
part of Story #21. This adds tools for future models and migrations; no
application models or tables are defined yet. The health endpoints keep their
existing behavior, and Docker Compose is unchanged.

### Install and check migrations on Windows

Start Docker Desktop and PostgreSQL using the earlier instructions. From the
repository root, load `.env` into your PowerShell process using the same `PG*`
loader above, then run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic check
```

Run these commands from `backend`, where `alembic.ini` lives.
`upgrade head` applies pending migrations. There are no migration revisions yet,
so it creates only Alembic's own empty `alembic_version` tracking table.
`current` shows the applied revision; it has no revision to print at this stage.
`check` compares the database with `Base.metadata`; expect
`No new upgrade operations detected.` No users, quizzes, materials, or other
application tables should appear.

When a future feature actually adds a model, import that model in
`alembic/env.py` so Alembic sees it, then use:

```powershell
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "Describe the model change"
# Read and review the generated file in alembic/versions before applying it.
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

Do not create an empty revision just for this foundation. Keep model changes
and their migration files in the relevant feature issue. Alembic also supports
`downgrade -1` to undo the latest revision, but review its `downgrade()` first:
a future migration could remove data. Do not run it on this empty foundation.
Do not call `Base.metadata.create_all()`; use reviewed migrations for future
schema changes.

### What each new file does

- `app/database.py` contains the shared database objects in one small file.
  `URL.create("postgresql+psycopg", ...)` builds the SQLAlchemy connection URL
  from the existing `PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT`, and `PGDATABASE`
  environment variables. It handles password URL escaping for you. Required
  values must be loaded before importing this module; no password is stored
  in Python or `alembic.ini`.
- In that file, `create_engine(...)` creates the database engine and connection
  pool. It connects only when a connection is needed. The three-second timeout
  limits connection attempts. `SessionLocal = sessionmaker(bind=engine)` is a
  reusable factory: future code can use `with SessionLocal() as session:` to
  open a session and close it afterward. Writes will need an explicit
  `session.commit()`; this foundation performs no writes through a session.
- `class Base(DeclarativeBase)` is the shared parent for future ORM models.
  `pass` leaves it empty. Its `metadata` will describe tables once models exist.
- `alembic.ini` points to the migration folder and makes `app` importable.
  It deliberately contains no connection URL or credentials.
- `alembic/env.py` loads the same engine and `Base.metadata`. Online mode uses
  a real connection inside `with` blocks. Offline mode (`--sql`) prints migration
  SQL without connecting. Neither mode invents application tables.
- `alembic/script.py.mako` is the template used when generating a future revision.
  `upgrade()` applies a schema change; `downgrade()` describes how to reverse it.
- `alembic/versions/.gitkeep` keeps the empty revisions directory in Git.
- `tests/test_sqlalchemy.py` selects the existing dedicated test database using
  `TEST_PGDATABASE`, opens a session, and checks that
  `session.execute(text("SELECT 1")).scalar_one()` returns `1`. `text` marks SQL
  text for SQLAlchemy; `scalar_one` reads exactly one value. It does not modify
  development data or create tables. Like the existing connectivity test, it
  skips without test settings and refuses the development database's name.
- `requirements.txt` adds pinned SQLAlchemy 2 and Alembic dependencies, reusing
  the existing psycopg driver.

To run all tests, load `.env` from the repository root first, then:

```powershell
$env:TEST_PGDATABASE = 'csmqp_test'
cd backend
.\.venv\Scripts\python.exe -m pytest
```

Reuse `csmqp_test` created earlier. Expect four passing tests. Without
`TEST_PGDATABASE`, expect two passing tests and two skipped integration tests.

## Part 1 Deliverables

| Deliverable | Standard | Location | Owner |
|---|---|---|---|
| Software Requirements Specification | IEEE 830-1998 | `docs/SRS/` | TBD |
| Test Plan & Test Cases | IEEE 829-2008 | `docs/TestPlan/` | TBD |
| Architecture & Design Specification | IEEE 1016-2009 | `docs/Architecture-Design/` | TBD |

## Requirements Traceability

Requirements (FR, NFR, SEC) in the SRS map to architecture components in the
SDD and to test cases in the Test Plan. See the RTM in Section 5 of the SRS.

## Team

| Name | GitHub | Role |
|---|---|---|
| Member 1 | @username | TBD |
| Member 2 | @username | TBD |
| Member 3 | @username | TBD |

## Contributing

1. Clone: `git clone https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform.git`
2. Work only in your own deliverable folder to avoid merge conflicts.
3. Run `git pull` before every push.
4. Use clear commit messages, e.g. `Update SRS: add SEC-03`.
5. For final submissions, open a Pull Request and assign reviewers.
