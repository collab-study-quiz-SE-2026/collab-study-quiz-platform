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
    │   └── main.py
    ├── tests/
    │   └── test_health.py
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
Only the `/health` application endpoint is implemented. FastAPI also provides
its default API documentation at `/docs`.
The existing test plan's TC-11 uses `/healthz` for a future availability test;
this exercise uses `/health` and does not implement that soak test.
Authentication, database integration, and the other planned features remain
separate work. Story #21 is not complete with this setup alone.

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
