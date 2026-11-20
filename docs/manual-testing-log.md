# Manual Testing Log

Record of the Member 2 baseline and manual checks reported during the local end-to-end pass. This log records results; it does not imply that known defects have been fixed or that all stories are complete.

## Run details

### Supplemental check — Materials filters (November 11, 2026)

- **Story:** #9 Search and Filter Materials (also supports #8 categorization)
- **Result reported by user:** Pass. A matching material appeared with search, subject, topic, and tag filters combined; tag search worked; clearing filters restored all uploaded files.
- **Observed behavior/follow-up:** Subject, topic, and tag fields require exact values. The user considers that workable for now; partial-value matching is future work, not a current defect.
- **Test-plan mapping:** There is no dedicated materials-search case in the provided plan. TC-05 covers question search, so this is a supplemental story-level browser check; automated materials filters have their own pytest cases.
- **Evidence limitation:** Result was reported by the user in chat; no screenshot or browser trace was saved.

### Supplemental check — Completed attempt history (November 11, 2026)

- **Story:** #16 Track Quiz Attempt History
- **Result reported by user:** Pass. A quiz completed yesterday appeared with the correct score and completion time.
- **Still pending:** Empty-history state for a student with no completed quiz attempts.
- **Evidence limitation:** Result was reported by the user; no screenshot or browser trace was saved.

### Supplemental check — Populated analytics and refresh (November 11, 2026)

- **Stories:** #17 View Performance Dashboard, #18 Analyze Topic-Wise Performance, #19 Visualize Learning Progress
- **Result reported by user / screenshots supplied:** Pass for displaying populated overview, topic performance, and learning progress for one quiz attempt (50% score; Database Systems topic).
- **Refresh:** User clicked Refresh; views continued working and values stayed the same because no new quiz data was added.
- **Limitation:** One attempt is enough to smoke-test populated rendering, but not to validate meaningful cohort percentiles or score trends. Screenshots were shared in chat and are not stored in the repository.

### Supplemental check — Analytics refresh after second quiz (November 11, 2026)

- **Stories:** #16–#19
- **Result reported by user / screenshots supplied:** Pass. After completing another quiz on Database Systems and refreshing, Overview showed 2 attempts, 75% average, both recent results (50% and 100%) and topic accuracy 3/4 (75%). Topic performance showed 2 quizzes/4 questions and 75% accuracy. Learning progress showed two points and an improving trend. Attempt History showed both completed attempts with matching scores and completion times.
- **Evidence limitation:** Screenshots were supplied in chat but are not stored in the repository. Two attempts verify that the UI refreshes with new data; they do not establish statistically meaningful cohort or trend calculations.

### Supplemental check — Invalid login recovery (November 11, 2026)

- **Story:** #3 User Login and Logout
- **Result reported by user:** Pass. An incorrect password displayed an error; entering the correct password immediately afterward succeeded without refreshing the page.
- **Evidence limitation:** User-reported; no screenshot or browser trace saved. Actual JWT expiration recovery remains untested.

### Supplemental check — Material search with no matches (November 11, 2026)

- **Story:** #9 Search and Filter Materials
- **Result reported by user:** Pass. Searching for a nonexistent material displayed the helpful no-match message asking the user to try different values or clear filters.
- **Evidence limitation:** User-reported; no screenshot or browser trace saved.

### Supplemental check — Empty attempt history (November 11, 2026)

- **Story:** #16 Track Quiz Attempt History
- **Result reported by user:** Pass. A student with no attempts saw the “No quiz attempts yet, join a quiz…” empty-state guidance.
- **Evidence limitation:** User-reported; no screenshot or browser trace saved.

### Supplemental check — Question category/difficulty filters (November 11, 2026)

- **Story:** #13 Categorize Questions
- **Result reported by user:** Pass. A newly created test question appeared for matching subject/topic/difficulty values; combinations with no matching question showed no-match feedback.
- **Evidence limitation:** User-reported; exact values and screenshots were not saved.

### Supplemental check — Question ownership and edit propagation (November 11, 2026)

- **Story:** #12 View and Manage Questions
- **Result reported by user:** Pass. Creator could edit their test question; the edit appeared in moderator and another student's view. Another student did not see edit/delete controls for that question.
- **Limitation:** This verifies visible UI controls and propagation. A direct unauthorized API edit/delete attempt was not made in this browser check.

### Supplemental check — Moderator rejection (November 11, 2026)

- **Story:** #14 Question Moderation
- **Result reported by user:** Rejection flow works.
- **Finding:** Moderator message box is too small to read the message comfortably. Logged as BUG-004 (Low usability); no fix applied.
- **Visibility:** The creator saw the question marked Rejected in My Questions; a second student's public Question Bank did not show the rejected question.
- **Reason visibility:** The user confirmed the creator can read the moderator's rejection reason.

### Supplemental check — Quiz creation and room joining (November 11, 2026)

- **Stories:** #26 Create and Configure Quizzes; #27 Participate in Quizzes; #28 Submit and Evaluate Quizzes; #29 Real-Time Quiz Updates
- **Result reported by user:** Quiz creation and valid joining work. An invalid room code is rejected with “No room found.” The host's send-question action starts the question immediately.
- **Combined evidence:** Earlier user-reported multi-tab test with one moderator and two students waited for both answers, revealed correctness/scores, advanced to the next question, showed a final leaderboard and recorded attempts in history.
- **Still unverified:** Timeout and reconnect edge cases; live quiz flow through the TLS WSS proxy.

### Supplemental check — Markdown material upload (November 11, 2026)

- **Stories:** #6 Upload Study Materials; #7 Browse and Download Materials
- **Result reported by user:** Valid Markdown upload works, as does the previously tested PDF. The user clarified that their invalid-file attempt was rejected as expected; the exact file type/content was not specified.

### Supplemental check — Live quiz timeout (November 11, 2026)

- **Story:** #29 Real-Time Quiz Updates
- **Result reported by user:** A student who did not answer before the round timed out received 0% for that question. Host waited to send the next question.
- **Status:** Timeout scoring and reconnect/resume passed (user-reported).
- **Reconnect follow-up:** User re-entered using the room key and resumed at the current quiz stage; pass reported.
- **Timer observation:** Live rounds use a fixed 30-second timer despite the configured quiz duration. This matches `ROUND_SECONDS` in the current implementation and `docs/REALTIME_QUIZ.md`; clarify whether the live quiz should instead honor the configured duration before treating this as a defect.

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
