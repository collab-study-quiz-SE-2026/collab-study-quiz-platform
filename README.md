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
├── docs/
│   ├── SRS/
│   │   └── CSMQP_SRS_v1.0.pdf
│   ├── TestPlan/
│   │   └── CSMQP_Test_Plan_v1.0.pdf
│   └── Architecture-Design/
│       └── CSMQP_SDD_v1.0.pdf
└── src/
```

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