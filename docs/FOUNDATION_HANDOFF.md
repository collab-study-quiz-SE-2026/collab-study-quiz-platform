# Story #21 foundation handoff

Local acceptance checks were executed on **October 31, 2026**, on Windows with
Docker Desktop / WSL 2, Python 3.12.14, and Node.js 22.19.0.
The implementation is ready for review; Story #21 stays open until the team
reviews and merges the completion PR and accepts the results below.

## Acceptance evidence

| Story #21 criterion | Implementation and executed evidence |
|---|---|
| Frontend/backend initialized and integrated | React/Vite/TypeScript build passed; real browser at localhost:5173 showed Backend connected; frontend served over certificate-verified HTTPS |
| PostgreSQL 15+ connectivity | Existing persistent PostgreSQL 15 service; database health check, SQLAlchemy SELECT 1, and dedicated database tests passed |
| S3-compatible storage | RustFS 1.0.4, named volume, configured bucket; signed SDK write/read/delete test passed; bucket persisted after restart |
| REST and WebSocket integration points | Three REST health routes plus restored ping/pong WebSocket; real WSS connection returned pong |
| HTTPS/WSS with TLS 1.3 | Caddy 2.11.7; CA/hostname verified, TLSv1.3 negotiated, HTTPS frontend and API checks passed, WSS passed, TLS 1.2 rejected |
| Environment setup documented | FOUNDATION_SETUP.md covers a fresh clone, local settings, startup, migrations, bucket setup, tests, secure checks, and stopping |
| Application runs locally | Host FastAPI/Vite and local Compose services exercised together |
| Secrets excluded | Only examples committed; .env, .local-certs, private keys, dependency/build folders, and Python caches ignored; CA private key remains in named volume |
| Parameterized relational access | Constant SELECT 1 probes; SQLAlchemy bound-parameter test returned SQL-looking input as data without executing it; no application tables created |

## Results

- Full pytest suite with `TEST_PGDATABASE=csmqp_test` and
  `RUN_STORAGE_TESTS=1`: **13 passed**, no skips, in 10.23 seconds.
- One existing upstream Starlette/HTTPX deprecation warning remains.
- Without integration settings: **10 passed, 3 skipped** as documented.
- `pip check`: no broken requirements. Anonymous bucket access returned HTTP 403.
- `npm.cmd run build`: TypeScript checking and production build passed.
- `alembic upgrade head`, `current`, and `check` passed. There are no revisions
  yet; only `alembic_version` exists in the development database.
- Bucket setup ran twice successfully, confirming repeatable initialization.
- Stopping storage produced HTTP 503 with `{"detail":"Storage unavailable"}`;
  restarting preserved the existing bucket and restored secure health checks.
- TLS verifier output:

```text
Certificate verified; negotiated TLSv1.3
HTTPS frontend: 200
HTTPS /api/health: 200
HTTPS /api/health/db: 200
HTTPS /api/health/storage: 200
Certificate-verified WSS: ping -> pong
TLS 1.2 correctly rejected
```

PR #40 had reverted the original WebSocket work. The user explicitly requested
its restoration for this completion task. The restored tests allow both the
Vite and secure local origins. No quiz WebSocket behavior is implemented.

## Handoff to the teammate owning #22

No GitHub Actions files were added or modified. The teammate can build CI
around these existing commands after reviewing/merging the completion PR:

1. Frontend: `npm ci`, then `npm run build` from `frontend`.
2. Backend: install `backend/requirements.txt` in a clean environment.
3. Start a disposable PostgreSQL service and a dedicated test database; provide
   the `PG*` variables and `TEST_PGDATABASE`.
4. For the storage integration check, start the S3-compatible service, provide
   disposable `S3_*` values, initialize its bucket, and set `RUN_STORAGE_TESTS=1`.
5. Run `python -m pytest` from `backend`. Do not treat skipped integration checks
   as proof of live service connectivity.
6. Check Alembic upgrade/check against a disposable database.

The local TLS smoke check uses Docker Desktop's `host.docker.internal`. The CI
owner should choose the appropriate runner/network arrangement before adding
that check to hosted CI; this branch does not guess a GitHub runner setup.

Further application work stays on feature branches. Final branch protection,
release settings, public-domain certificates, deployment networking, and final
integration follow #22. Local Caddy is a small lab fixture; the SDD's intended
Nginx deployment can be addressed at that integration stage. The local CA is
not installed in Windows trust and no browser certificate warning was bypassed.

This foundation adds no users, materials, quizzes, ORM application models,
upload API, authentication changes, or production deployment. No named volume
was deleted or reset. The signed storage probe only removes its own UUID key.
