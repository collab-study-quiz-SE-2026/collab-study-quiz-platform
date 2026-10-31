# Collaborative Study Material & Quiz Platform (CSMQP)

A Software Engineering student project for sharing study materials,
collaborating on questions, playing quizzes, and tracking learning progress.

## Start here

**[Windows setup, commands, and code explanations](docs/FOUNDATION_SETUP.md)**

**[Story #21 verification and handoff to CI Story #22](docs/FOUNDATION_HANDOFF.md)**

## Current foundation

- React + Vite + TypeScript frontend with a backend connection indicator.
- FastAPI REST health checks and a small WebSocket ping/pong connection.
- PostgreSQL 15 with persistent data, SQLAlchemy 2 sessions, and Alembic setup.
- S3-compatible RustFS storage with a persistent bucket and an S3 client.
- Caddy serving the built frontend, HTTPS API routes, and WSS with TLS 1.3.
- Environment-based credentials, ignored local secrets, and parameterized SQL.

Authentication, application tables, materials, quizzes, and analytics belong
to their own feature issues. The storage foundation does not implement uploads.

## Local addresses

| Address | Purpose |
|---|---|
| `http://localhost:5173` | Vite development frontend |
| `http://127.0.0.1:8000/health` | Backend process check |
| `http://127.0.0.1:8000/health/db` | Real PostgreSQL `SELECT 1` |
| `http://127.0.0.1:8000/health/storage` | Signed S3 bucket connectivity check |
| `ws://127.0.0.1:8000/ws/health` | Development WebSocket: `ping` -> `pong` |
| `https://localhost` | Built frontend through the local TLS proxy |
| `https://localhost/api/health` | HTTPS backend check |
| `wss://localhost/ws/health` | Secure WebSocket check |

HTTPS uses a private local CA, not a publicly trusted certificate. The setup
guide shows verification with its public CA certificate without changing
Windows trust. Local HTTP development ports stay available on this machine.
Public deployment and release configuration follow the team's CI/integration stage.

## Repository

```text
backend/app/          FastAPI endpoints, database setup, S3 client
backend/tests/        API, CORS, database, storage, WebSocket tests
backend/alembic/      Migration environment and future revisions
backend/setup_storage.py   Idempotent bucket initialization
backend/verify_tls.py      Certificate-verified HTTPS/WSS check
frontend/             React + Vite + TypeScript
docker-compose.yml    PostgreSQL, RustFS, Caddy; persistent named volumes
Caddyfile             Local TLS 1.3, API/WebSocket proxy, static frontend
.env.example          Safe local configuration template
docs/                 Setup guide and original SRS, SDD, and test plan PDFs
```

## Team workflow

Story [#21](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/21)
covers the foundation. Story [#22](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/22)
is the teammate-owned GitHub Actions task; this change adds no workflow files.
Keep subsequent feature work on feature branches. Coordinate final integration,
release settings, and deployment after #22 is ready. Open PRs for review and
do not merge someone else's work automatically.

The original SRS, architecture/design specification, and test plan PDFs in
`docs/` remain the requirement sources. See the SRS requirements traceability
matrix for their feature and test mappings.
