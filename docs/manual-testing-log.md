# Manual Testing Log

Record of the Member 2 baseline and manual checks reported during the local end-to-end pass. This log records results; it does not imply that known defects have been fixed or that all stories are complete.

## Run details

- **Date:** November 10, 2026
- **Repository revision used as base:** `main` at `61487721390175fa9a1bfee80508cbd4cd287106` (`6148772`)
- **Working branch:** `codex/reconcile-frontend-full-ui`
- **Environment:** Windows, local FastAPI, Docker PostgreSQL 15, RustFS, and Caddy
- **Account details:** Two student accounts and one locally promoted moderator were used. Emails and credentials are intentionally omitted.
- **Code state:** Frontend reconciliation and quiz WebSocket client are committed as `1357ca2` on PR #67, which is open and not merged.

## Automated checks

| Check | Result | Notes |
| --- | --- | --- |
| Backend pytest baseline | **131 passed, 2 skipped** | Run against the latest `main` snapshot with coverage; 87% total coverage. The skipped cases required optional storage integration settings. |
| Frontend production build | **Passed** | `npm run build` completed after the WebSocket client changes. |
| PR #67 CI | **Backend job failed; frontend build passed** | Backend job stopped at `python -m alembic check`: it detected removals for the materials table and indexes. The same latest-main commit (`6148772`) also has a failed CI run, so this failure predates the frontend branch. Backend pytest did not run in the PR job after the migration check failed. |
| Python package consistency | **Not included in this baseline record** | No result recorded for this pass. |

## User-reported browser and local-service checks

| Area | Result | Details |
| --- | --- | --- |
| Registration and login | **Passed** | Registration created a student account; login succeeded. |
| Session persistence | **Passed** | The signed-in session remained after refreshing the page. |
| Logout and login again | **Passed** | The user logged out and logged in again successfully. |
| Logout token invalidation | **Passed** | Reusing the saved token at `GET /auth/me` after logout returned **401**. The token itself is not recorded. |
| Student/moderator authorization | **Passed** | A student request to the moderation endpoint returned **403**. The moderator account showed moderation access. |
| Question moderation and visibility | **Passed** | A moderator approved a question; a different student then saw the approved question in the Question Bank. Pending questions remain unavailable in the public browse list until approved. |
| Live quiz flow | **Passed over development WebSocket** | In separate browser tabs, one moderator selected two questions and started a quiz; two students joined and participated. Each question stayed open until both students answered, then the correct answer and current scores appeared. The moderator advanced to question two, the same answer/reveal cycle completed, and the final leaderboard appeared. The students' attempts appeared in Attempt History. The reported run used the development WebSocket; it did not establish that this authenticated quiz-room flow was tested through the HTTPS/WSS proxy. |
| Study-material storage | **Passed manually with local RustFS** | Storage health returned `status: ok`; a student uploaded a PDF; another student could see and download it. |
| Unsupported material type | **Rejected as expected** | Uploading a `.txt` file displayed an error. A small layout concern in that area is separately recorded as BUG-003. |
| Subject/topic material filters | **Working as exact matches** | The user confirmed that the filters require the specific full value. This was considered workable and was not logged as a defect. |
| Cross-user private-data access | **403 observed** | A student access attempt for another user's private data returned **403**. The exact endpoint was not recorded in the conversation. |
| Own analytics API access | **Passed** | As a student, these endpoints each returned **200**: `/quiz-attempts/me`, `/dashboard/performance`, `/analytics/topics`, and `/analytics/progress`. Response bodies were not captured in the log. |

## HTTPS, WSS, and TLS verification

The user ran `backend/verify_tls.py` and reported the following actual output:

```text
Certificate verified; negotiated TLSv1.3
HTTPS frontend: 200
HTTPS /api/health: 200
HTTPS /api/health/db: 200
HTTPS /api/health/storage: 200
Certificate-verified WSS: ping -> pong
TLS 1.2 correctly rejected
```

This verifies the HTTPS frontend/API, PostgreSQL and RustFS health checks, the `/ws/health` WSS connection, TLS 1.3 negotiation, and TLS 1.2 rejection. It does **not** verify an authenticated quiz-room session at `/ws/quizzes/{room_code}` over WSS; the live quiz browser flow above used the development WebSocket.

## Open defects and follow-up

See [bug-report-log.md](bug-report-log.md) for reproduction details. No fixes have been made during this reporting pass.

- **BUG-001 — Missing tags accepted:** Known acceptance mismatch for #6; the upload endpoint accepts an empty tag list although tags are required by the story. Not re-tested during this browser pass.
- **BUG-002 — Moderator quick-login fallback:** The shortcut can register a student if the preset moderator account is absent. A local account was promoted directly in PostgreSQL for testing; no public registration-to-moderator path exists by design.
- **BUG-003 — Material card title overflow:** A long underscore-separated material title extends beyond the card border; screenshot evidence is referenced in the bug log.
- **Analytics UI:** The own-account analytics APIs respond successfully, but dashboard/topic screens are not wired into the current frontend; the progress chart is not connected to app navigation.
- **Authenticated quiz WSS:** The secure transport health check passed, but the live quiz event flow has not yet been run through the HTTPS/WSS proxy.
- **Other untested cases:** Login with invalid credentials, JWT expiry by time, oversized upload, malformed PDF content, empty upload, and browser accessibility/responsive checks.

## Scope notes

- Search filters requiring exact subject/topic values were accepted by the user as workable; no defect was filed for that behavior.
- The checks above do not close GitHub stories or prove the remaining frontend analytics, performance benchmark, soak/availability, or demo requirements are complete.
