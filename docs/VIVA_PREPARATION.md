# Viva preparation guide

Use this to study the project and explain decisions in your own words. Be candid about what is implemented, what is tested, and what remains planned.

## 60-second project explanation

CSMQP is a collaborative study platform. Students register, contribute questions, study shared PDF/Markdown materials, and take quizzes. Moderators review submitted questions and host live quiz rooms. FastAPI exposes REST endpoints and WebSockets; PostgreSQL stores users, questions, quizzes, and attempts; RustFS stores uploaded files; React and TypeScript provide the browser UI. Docker Compose runs local services, Alembic tracks schema changes, and GitHub Actions runs automated checks.

## Architecture and request flow

- **React + TypeScript:** renders screens and sends HTTP requests through `frontend/src/api.ts`. The browser keeps the bearer access token in session storage and sends it in the `Authorization` header.
- **FastAPI:** validates request bodies, applies authentication/role checks, runs business logic, and returns JSON. CORS allows the local frontend origin.
- **SQLAlchemy + PostgreSQL:** SQLAlchemy maps Python models to tables and executes parameterized statements through database sessions. Alembic applies versioned schema migrations.
- **RustFS:** S3-compatible object storage receives material bytes. PostgreSQL stores searchable metadata and the storage key. Downloads check authorization before returning a file.
- **WebSockets:** the host and students connect to a room. The server broadcasts the active question, accepts answers, ends a round after answers or the 30-second timer, and reveals results at the right point.
- **Docker Compose:** provides PostgreSQL and RustFS locally. HTTPS/WSS through Caddy is verified with the repository TLS script.

## Likely viva questions

### Why use PostgreSQL and SQLAlchemy?

PostgreSQL provides persistent relational storage and constraints for related entities. SQLAlchemy lets the application work with model objects and sessions; values are bound as parameters, which keeps input data separate from SQL syntax. Alembic records schema changes so a fresh or existing database can be upgraded reproducibly.

### How does authentication work?

Registration hashes the password before saving it. Login verifies the submitted password and returns a signed, expiring JWT. Protected requests send that token as a bearer token. The backend checks it and loads the user before running the route. Logout increments a token version so an older token is rejected. Do not claim that browser recovery after a naturally expired token was verified unless you run that check.

### How is role-based access enforced?

The frontend hides actions a role should not use, but that is only a usability control. FastAPI dependencies enforce permissions on the server, so a caller cannot gain access merely by editing browser code. Explain the specific routes/tests you verified rather than claiming every route had a full manual audit.

### How does question moderation work?

Student questions enter a pending state. A moderator can approve or reject them and attach a reason. Approved questions appear in public browse/quiz selection; rejected questions remain visible to their creator with their status and reason, while other students do not see them in the public Question Bank.

### How are materials stored?

The application validates the upload type and size, stores the bytes in RustFS, and saves metadata in PostgreSQL. Other authenticated students can list and download shared material. Never commit local `.env` credentials; use `.env.example` as a template.

### How do live quizzes work?

The host creates a room and controls question progression. Students join with a room code and submit answers. The server tracks the room, waits until everyone answers or the 30-second round timer expires, then sends results. The recent browser run verified two students, scoring, leaderboard, timeout scoring, and reconnect by re-entering the room. Explain that same-account duplicate tabs caused confusion during testing; multi-account participation is the validated scenario.

### What do the analytics show?

The dashboard aggregates completed attempts, average scores and times, recent results, and topic accuracy. Topic performance groups results by subject/topic. Learning progress plots scores over attempts. The browser run with two quizzes showed counts and values updating after refresh. Two attempts are a functional smoke test, not a statistically meaningful cohort or trend study.

### What testing was done?

The recorded full backend run passed 133 tests with zero skips while the two RustFS integration checks were enabled. The frontend production build passed. Browser checks were performed by the team and recorded as user-reported results; distinguish them from automated evidence. The exact TC-06 latency measurement, 1,000-attempt analytics benchmark, 24-hour/50-user soak test, and endpoint-level SQL injection scenarios remain planned.

### What is one known requirement question?

Live quiz rounds use a fixed 30-second timer. The quiz duration field is used as an overall limit in the REST attempt flow. The team should confirm whether the configured duration is intended to change live round timing. Describe this as an open requirements decision, not as a verified defect.

## Before the viva

1. Run the system from a clean checkout using README instructions and explain each service.
2. Demonstrate student registration/login, moderator question review, shared material upload/download, and a two-student live quiz.
3. Show analytics updating after a second attempt and explain the small sample limitation.
4. Open CI and explain what each job checks; show one meaningful test and its assertion.
5. Review the bug log and deferred requirements. State clearly what passed, what is pending, and why.
6. Read each section of this guide, close it, and rehearse the explanations without memorizing the wording.
