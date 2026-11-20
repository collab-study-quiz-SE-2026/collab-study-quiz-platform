# Submission checklist

Working checklist for final packaging. Mark each item Ready only after checking the instructor's deliverables checklist and required file formats. Demo recording and deadline dates are intentionally omitted per the team's decision.

| Deliverable | Current artifact / evidence | Status / next action |
| --- | --- | --- |
| Software Requirements Specification | `docs/CSMQP - Software Requirements Specification (SRS)-3.pdf` | Present; check final feature descriptions against the delivered implementation. |
| Software Architecture and Design Specification | `docs/CSMQP - Software Architecture & Design Specification (SDD)-1.pdf` | Present; confirm diagrams and design match final architecture. |
| Software Test Plan and test cases | `docs/CSMQP - Software Test Plan & Test Cases-1.pdf` | Present; include execution outcomes and distinguish partial/pending cases using `docs/qa-2026-11-11/`. |
| Implementation / source code | GitHub repository, `main` | Present; verify final PRs are merged and record final commit SHA. |
| Test execution evidence | `docs/qa-2026-11-11/`, `docs/manual-testing-log.md` | Present; keep automated output separate from user-reported manual checks. |
| Defect log and retest evidence | `docs/bug-report-log.md` | Present; BUG-001/003 owned by Shubham; BUG-004 low severity and intentionally deferred. Update final statuses after retesting. |
| User/setup guide | `README.md`, `docs/FOUNDATION_SETUP.md` | Present; perform a fresh-clone check and ensure Windows startup steps still work. |
| CI evidence | GitHub Actions checks on final PRs | Check all required workflows pass on the final revision and capture links. |
| Final run instructions / environment | README and `.env.example` | Ensure no secrets are included; verify Docker-backed setup. |
| Presentation / viva preparation | `docs/VIVA_PREPARATION.md` | Use for study; adapt answers in your own words and be ready to explain limitations. |

## Deferred verification to disclose

Actual JWT expiry recovery, endpoint-level malicious-input checks, measured WebSocket latency, analytics performance with 1,000 attempts, 24-hour/50-user availability testing, and representative cohort validation have not been completed in this pass. The live quiz uses 30-second rounds; whether this should follow configured quiz duration remains a requirements decision. Do not mark these as passed without new evidence.
