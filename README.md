# Collaborative Study Material & Quiz Platform (CSMQP)

A Software Engineering student project for sharing study materials,
collaborating on questions, playing quizzes, and tracking learning progress.

## Start here

**[Windows setup, commands, and code explanations](docs/FOUNDATION_SETUP.md)**

**[Story #21 verification and handoff to CI Story #22](docs/FOUNDATION_HANDOFF.md)**

## Current foundation

- React + Vite + TypeScript frontend with a backend connection indicator.
- FastAPI REST health checks and authenticated quiz-room WebSocket updates.
- PostgreSQL 15 with persistent data, SQLAlchemy 2 sessions, Alembic migrations,
  and a small users table for authentication.
- Student registration, Bcrypt password hashing, 60-minute signed JWT login,
  logout invalidation, and server-side Student/Moderator authorization checks.
- S3-compatible RustFS storage with a persistent bucket and an S3 client.
- Caddy serving the built frontend, HTTPS API routes, and WSS with TLS 1.3.
- Environment-based credentials, ignored local secrets, and parameterized SQL.

Quiz creation, participation, answer evaluation, and private attempt history are
implemented as backend API foundations. The storage foundation does not yet
implement study-material uploads, and the frontend still needs to integrate the
quiz workflows.

## Quiz API notes

- Creating a quiz requires a JWT. The response includes the room code for the
  host. Authenticated quiz list/detail responses omit that code.
- The host opens the active question with
  `PATCH /quizzes/{quiz_id}/active-question` and JSON `{"position": 0}`. The
  position is zero-based.
- An authenticated host or student with an active attempt can connect to
  `ws://127.0.0.1:8000/ws/quizzes/{quiz_id}` and send
  `{"type": "authenticate", "token": "<JWT>"}` as the first message. The
  server then sends the current quiz state, followed by `question_changed`,
  `answer_submitted`, and `attempt_completed` events as those actions happen.
- Student attempt history is available at `GET /quiz-attempts/me`; summary and
  daily average scores are at `GET /quiz-attempts/me/trends`. Both require a
  JWT and only return the signed-in student's data.

The WebSocket event broadcaster is in memory for this student project, so it
coordinates clients connected to the same backend process. Database records
remain the source for quiz and attempt state.

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
backend/app/          FastAPI endpoints, authentication, database setup, S3 client
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
