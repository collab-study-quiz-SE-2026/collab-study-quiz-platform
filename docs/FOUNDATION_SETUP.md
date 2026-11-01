# Local foundation setup on Windows

Use PowerShell. Prerequisites: Git, Python 3.12+, Node.js 22.19+ or a supported
newer LTS, and the existing Docker Desktop installation with WSL 2 and Linux
containers. Each teammate creates their own local environment files.

## 1. Configure a fresh clone

```powershell
git clone https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform.git
cd collab-study-quiz-platform
Copy-Item .env.example .env
notepad .env
```

Replace `PGPASSWORD`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, and `JWT_SECRET_KEY`
with your own local values. Use uppercase letters/digits for the S3 access key,
a long random storage secret, and a different long random JWT secret. Keep
values unquoted and without spaces for the simple loader below.
Do not overwrite an existing `.env`; add missing settings from the example.
Keep `FRONTEND_ORIGIN=http://localhost:5173,https://localhost` for both local modes.
All published Compose ports bind to `127.0.0.1`.

Start Docker Desktop from the Start menu and wait for the engine. Check:

```powershell
docker --version
docker compose version
docker info
docker compose config --quiet
docker compose up -d --wait db
docker compose up -d storage
curl.exe --fail http://127.0.0.1:9000/health
```

The last command should report RustFS `status: ok`. Allow a few seconds on first
startup. `config --quiet` validates without printing the resolved credentials.
PostgreSQL and storage use separate named volumes. No existing database is reset.

## 2. Backend terminal

Begin in the repository root. Compose reads `.env` automatically; Python does
not. Load the values into this PowerShell process without evaluating them as code:

```powershell
Get-Content .env | ForEach-Object {
    if ($_ -match '^[A-Z][A-Z0-9_]*=') {
        $parts = $_ -split '=', 2
        [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
    }
}
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe setup_storage.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Create `.venv` only once. Use `python` instead of `py` if that is how your Python
installation is registered. Calling the environment's executable directly avoids
activation or execution-policy changes. Keep this terminal open. The bucket setup
checks for the configured bucket and creates it only when absent; it never resets
data. The default region is `us-east-1` for this local storage service.

`upgrade head` creates the `users` table used for local authentication, then
records revision `20261101_0001` in Alembic's tracking table. From `backend`,
also check:

```powershell
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic check
```

`current` should show `20261101_0001`. `check` should say
`No new upgrade operations detected.` Future model features should import their
models in `alembic/env.py`, generate a revision with
`alembic revision --autogenerate -m "Describe the change"`, review its code,
and run `alembic upgrade head`. Do not call `Base.metadata.create_all()` or
create empty revisions for this foundation.

## 3. Frontend terminal

Begin in the repository root:

```powershell
cd frontend
Copy-Item .env.example .env
npm.cmd ci
npm.cmd run dev
```

Copy the example only once. Leave `VITE_API_URL` blank for automatic local
configuration: the Vite page uses `http://127.0.0.1:8000`; the HTTPS build uses
same-origin `/api`. An explicit URL overrides this, so avoid leaving an old
HTTP override in place when checking HTTPS. Restart/rebuild after changing it.
`VITE_*` settings are public browser values; never put credentials in them.

Open `http://localhost:5173`, expect **Backend connected**, and try **Check
connection**. The Account panel lets you register with an email and password,
then log in and out. New accounts are always `student` accounts. The signed JWT
is kept only in this browser tab's session storage and expires after 60 minutes.
Stopping FastAPI should show unavailable after retry; restarting and retrying
should recover. The indicator checks the REST process endpoint, not database or
storage readiness. The fixed dev port prevents accidental CORS port changes.
CORS is not authentication.

## 4. HTTPS and WSS terminal

Keep FastAPI running on port 8000. Build the frontend, then start the proxy:

```powershell
cd frontend
npm.cmd run build
cd ..
docker compose up -d proxy
docker compose exec proxy caddy validate --config /etc/caddy/Caddyfile
New-Item -ItemType Directory -Path .local-certs -Force | Out-Null
$proxyContainer = docker compose ps -q proxy
docker cp "${proxyContainer}:/data/caddy/pki/authorities/local/root.crt" .local-certs/root.crt
.\backend\.venv\Scripts\python.exe backend/verify_tls.py
```

This verifies the CA and hostname, requires TLS 1.3, fetches the built frontend
and the process/database/storage API endpoints, and checks real WSS `ping` ->
`pong`. It also confirms TLS 1.2 is rejected. No certificate verification is
disabled. The proxy uses Docker Desktop's `host.docker.internal` to reach FastAPI.

Caddy creates its local CA in the `caddy_data` volume. Only the public root
certificate is copied out. This does **not** install a trusted root into Windows.
A browser may therefore warn at `https://localhost`. Do not click through the
warning. For browser use, the user can explicitly choose to trust this local CA;
the scripted checks work without that system change. Public-domain certificates,
hosting, and release configuration remain for the later deployment stage.

`Caddyfile` allows TLS 1.3 only. `/api/*` is forwarded to FastAPI after removing
`/api`; `/ws/*` is forwarded as-is. Other paths serve `frontend/dist`. HTTPS/WSS
is the secure local entry point; plaintext host ports are local development and
internal service connections. FastAPI and React are not containerized.

## 5. Full tests and direct checks

In a new PowerShell process, load `.env` from the repository root using the
loader in step 2. Create the dedicated test database once:

```powershell
docker compose exec db sh -c 'createdb -U "$POSTGRES_USER" csmqp_test'
$env:TEST_PGDATABASE = 'csmqp_test'
$env:RUN_STORAGE_TESTS = '1'
cd backend
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check
```

Reuse `csmqp_test` if it already exists. With the example origins, local storage
and test database configured, expect **17 passing tests**. Without the dedicated
test database, the authentication and database integration checks skip; without
storage settings, the storage round-trip check skips. The database tests issue
read-only statements against the dedicated test database. Authentication tests
create and remove only `auth-test-*` accounts in that dedicated database. The
storage test uses a UUID object under `foundation-checks/` and deletes only that
object in cleanup; it never clears a bucket. No study-material upload feature is
added.

Direct REST and PostgreSQL checks from the repository root:

```powershell
curl.exe -i http://127.0.0.1:8000/health
curl.exe -i http://127.0.0.1:8000/health/db
curl.exe -i http://127.0.0.1:8000/health/storage
docker compose exec db pg_isready
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;"'
```

Expect HTTP 200 with `status: ok`; the latter health endpoints also return
`database: connected` or `storage: connected`. Unavailable dependencies return
generic HTTP 503 responses without credentials. `/health` remains independent.
WebSocket `/ws/health` replies `pong` to `ping` and `Send ping` to other text.
Browser origins must be in `FRONTEND_ORIGIN`; native public health probes may
omit Origin. This is not the authenticated quiz-room WebSocket implementation.

## Files and important code

- `app/main.py`: the FastAPI object, health routes, and small authentication
  routes. Uvicorn imports it using `app.main:app`. CORS permits the configured
  frontend origins. The WebSocket loop awaits text and catches disconnects cleanly.
- `app/database.py`: `URL.create` builds a URL from `PG*` values; `create_engine`
  provides connections; `SessionLocal` opens reusable sessions; `get_db` closes
  each request's session. `Base` is the model parent.
- `app/models.py`: the small `users` table and the two roles: Student and
  Moderator. `app/auth.py` hashes/checks passwords, creates/validates JWTs, and
  rejects missing, expired, invalidated, or malformed tokens. `app/schemas.py`
  validates API input and keeps password hashes out of responses.
- `app/storage.py`: creates the S3 SDK client with environment credentials,
  signed requests, path-style addressing, and short timeouts. Secrets stay
  server-side. `closing(...)` closes the client after health/setup/test work.
- `setup_storage.py`: idempotent bucket setup; it never deletes existing data.
- `verify_tls.py`: local certificate, TLS-version, HTTPS, and WSS checks.
- `alembic.ini`, `alembic/env.py`, and `versions/20261101_0001_create_users_table.py`:
  connect migrations to the same engine and define the first `users` table revision.
  `script.py.mako` remains the template for future revisions.
- `frontend/src/main.tsx` mounts React; `App.tsx` fetches the health endpoint and
  provides the small register/login/logout form. CSS provides simple responsive styling.
  Vite and TypeScript config handle development and builds; npm's lockfile pins
  dependencies for teammates.
- `docker-compose.yml`: persistent PostgreSQL, RustFS, and Caddy services.
  `Caddyfile` terminates local TLS and routes requests. The original PostgreSQL
  volume is retained; all new services have their own named volumes.

## Authentication endpoints

Authentication uses the same PostgreSQL service. `POST /auth/register` validates
an email and 8-72 character password, hashes the password with Bcrypt cost 12,
and creates a `student` user. `POST /auth/login` returns a signed bearer JWT
with the user's id and role; it expires in 60 minutes. `POST /auth/logout`
increments a stored token version, so the current token can no longer be used.
`GET /auth/me` needs a bearer token. `GET /auth/users/{id}` only returns the
current student's own account, unless the user is a `moderator`.

There is deliberately no public endpoint for assigning the moderator role:
otherwise any new account could grant itself extra access. For this local lab,
an instructor can promote a trusted account directly in PostgreSQL after the
account exists:

```powershell
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "UPDATE users SET role = '\''MODERATOR'\'' WHERE email = '\''instructor@example.com'\'';"'
```

Use bound SQL parameters for future user input, for example
`session.execute(text("SELECT :value"), {"value": user_value})`. Never insert
input into SQL with f-strings. The SQLAlchemy integration test checks a
SQL-looking string is returned as data rather than executed. Existing probes
use constant `SELECT 1`; authentication queries use SQLAlchemy's bound values.
The `users` table is the only application table at this stage.

## Safe stopping and troubleshooting

Stop host servers with `Ctrl+C`. From the repository root:

```powershell
docker compose stop
```

Restart with the earlier `up -d` commands. Never use `docker compose down -v`
or delete the named volumes. Database passwords initialize a new PostgreSQL
volume only; editing `.env` does not change an existing database password.
If a port is occupied, identify the existing server before starting another one.
If storage is unavailable, check its container and run `setup_storage.py` after
loading the S3 settings. If the proxy cannot reach the backend, confirm FastAPI
is running and Docker Desktop's host networking is available.

Do not commit `.env`, `.local-certs`, private keys, virtual environments,
`node_modules`, or `dist`. The local CA's private keys remain in its Docker volume.
The examples contain placeholders only. Do not print resolved Compose config
or credentials in logs or screenshots.

Implementation references: [RustFS Docker setup](https://docs.rustfs.com/en/installation/container/docker),
[Caddy TLS](https://caddyserver.com/docs/caddyfile/directives/tls), and
[Caddy WebSocket proxy support](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).
