> Update, 11 November 2026: The snapshot below is historical. PR #67 integrated the feature screens; the current branch also contains analytics UI and the small materials/history fixes. See [submission readiness](qa-2026-11-11/submission-readiness.md) for current implementation and verification gaps. Do not use the old missing-screen statements as the current backlog.

# Epic and Story Integration Status

Snapshot of the repository at `main` commit `61487721390175fa9a1bfee80508cbd4cd287106` (November 10, 2026). This compares each story's GitHub acceptance criteria with code and tests that are actually present in this checkout. A feature in the backend is not counted as fully integrated if its user-facing frontend or required verification is missing.

This is an implementation and evidence map, not a change to issue status. It does not close stories or claim that an entire epic is complete.

## Overall view

- Backend foundations, authentication, question-bank APIs, materials APIs, quiz APIs, analytics APIs, and the real-time quiz WebSocket are present on `main`.
- The frontend on `main` contains the local connection check and registration/login/logout shell. It does not yet contain the full study-material, question-bank, quiz, analytics, or live-quiz screens.
- Automated backend coverage is substantial: the November 10 baseline run on this revision reported **131 passed, 2 skipped**, and **87% total coverage**. The two storage integration checks were skipped because optional storage test settings were not enabled. This result alone does not verify browser workflows, production-like storage, TLS, uptime, or analytics performance.
- The only confirmed acceptance mismatch currently recorded in `docs/bug-report-log.md` is BUG-001: material upload accepts a missing `tags` field although Story #6 says tags are required.

## Epic 1 — User Authentication & Profiles (#1)

| Story | Integration on `main` | Remaining for the whole story |
| --- | --- | --- |
| [#2 User Registration](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/2) | Backend registration, validation, duplicate rejection, bcrypt hashing, and tests are present. The main React shell has a registration form and confirmation message. | Recheck end-to-end browser registration against a fresh database and confirm the full acceptance flow after frontend feature integration. |
| [#3 User Login and Logout](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/3) | Backend login issues signed, expiring JWTs; logout invalidates the token version. The main React shell stores the token for the tab, restores the account, and logs out. | Browser-check invalid credentials, expiration, refresh/session behavior, and logout failure handling with the integrated app. |
| [#4 Role-Based Access Control](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/4) | Student/moderator roles and backend authorization checks exist; feature tests cover protected actions and private analytics. | Audit permissions across every integrated screen and endpoint, including cross-user access; this is broader than the currently tested cases. |

**Epic status:** Core authentication is integrated; finish a role-by-role end-to-end audit before calling the epic fully satisfied.

## Epic 2 — Study Material Management (#5)

| Story | Integration on `main` | Remaining for the whole story |
| --- | --- | --- |
| [#6 Upload Study Materials](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/6) | Authenticated PDF/Markdown upload, size/type validation, metadata persistence, and mocked-storage tests exist. RustFS client/configuration is present. | BUG-001: tags can be omitted. Run the real RustFS upload/download round trip; the baseline skipped this optional storage integration check. Frontend upload flow is not in the main app. |
| [#7 Browse and Download Materials](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/7) | Authenticated list/download endpoints, metadata responses, missing-object handling, and tests exist. | Integrate and browser-test listing/download UI; validate access and real object storage behavior. |
| [#8 Categorize Study Materials](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/8) | Material metadata supports subject/topic/tags, and list endpoints have category filters. | Verify the complete category/tag acceptance flow in the UI, including moderator taxonomy management if required by the intended interpretation of the issue. |
| [#9 Search and Filter Materials](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/9) | Backend list/search supports title, course code, tag, subject, and topic filters with tests. | Connect search/filter controls and empty-results feedback in the integrated frontend and verify matching behavior manually. |

**Epic status:** Backend paths are mostly implemented. Required tags and real RustFS verification remain; the user-facing material workflows are not integrated on `main`.

## Epic 3 — Collaborative Question Bank (#10)

| Story | Integration on `main` | Remaining for the whole story |
| --- | --- | --- |
| [#11 Create Questions](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/11) | Authenticated multiple-choice creation, validation, persistence, and retrieval APIs/tests exist. | Integrate the question screens into the main frontend and verify the complete browser flow. |
| [#12 View and Manage Questions](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/12) | List/detail/edit/delete APIs and creator/authorization checks are present with tests. | Integrate and browser-test the views and management actions; confirm ownership and moderator behavior in the UI. |
| [#13 Categorize Questions](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/13) | Subject, topic, difficulty fields, filters, and update preservation are implemented and tested. | Add/connect the category and difficulty controls to the main frontend, then verify the combinations manually. |
| [#14 Question Moderation](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/14) | Moderator queue, approve/reject actions, pending visibility rules, and access-control tests exist. | Integrate and test the moderator workflow in the main UI, including refresh and error states. |

**Epic status:** Backend story criteria are substantially represented. Frontend integration is the main remaining completion work.

## Epic 4 — Performance Analytics (#15)

| Story | Integration on `main` | Remaining for the whole story |
| --- | --- | --- |
| [#16 Track Quiz Attempt History](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/16) | Attempts persist score, question responses/timing, completion status/date; history API and privacy tests exist. | Add history screens to the main frontend and manually verify completed, empty, and private-access cases. |
| [#17 View Performance Dashboard](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/17) | Dashboard API calculates totals, averages, recent results, topic accuracy, timing, percentile, and trends; tests include empty state and privacy. | No dashboard screen is wired into the main frontend. The under-600 ms target has not been benchmarked against 1,000 attempts. |
| [#18 Analyze Topic-Wise Performance](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/18) | Topic analytics API calculates accuracy, average time, strengths/weaknesses, and cohort percentile where data exists; tests cover these calculations and access controls. | Add a topic analytics screen/filter to the main frontend. Validate percentile behavior with representative cohort data. |
| [#19 Visualize Learning Progress](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/19) | Progress API and `LearningProgressChart.tsx` exist; backend tests cover chronological history, empty state, and privacy. | The chart is not imported/rendered by `App.tsx` on `main`; wire it into navigation and verify refresh/update and low-data states. |

**Epic status:** Backend analytics are implemented and tested at functional level; all user-facing analytics and the latency target remain incomplete/unverified.

## Epic 5 — Platform Infrastructure & Quality Assurance (#20)

| Story | Integration on `main` | Remaining for the whole story |
| --- | --- | --- |
| [#21 Project Setup & Database Integration](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/21) | PostgreSQL 15 Compose service, SQLAlchemy/Alembic, RustFS, FastAPI, React/Vite foundation, REST health checks, health WebSocket, Caddy TLS 1.3 HTTPS/WSS, environment-based secrets, and parameterized SQL are present. Issue #21 is closed in GitHub. | This baseline run verified backend tests against PostgreSQL. It did not rerun the real RustFS round trip or certificate-validated HTTPS/WSS checks; run `backend/verify_tls.py` and the storage integration checks during the final local verification. |
| [#22 GitHub Actions CI Workflow](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/22) | CI is merged: backend tests with PostgreSQL, Alembic migration checks, and frontend production build are configured in `.github/workflows/ci.yml`. | Continue checking the workflow on subsequent PRs; no additional feature work is identified from the local code snapshot. |
| [#23 Integration Testing & Bug Fixes](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/23) | Bug log and testing guide exist. Baseline ran 131 tests successfully; 2 optional storage checks were skipped. | Test key workflows across the integrated frontend/backend, record each finding against the test plan, review/fix critical bugs in a separate pass, and retest. This issue is open. |
| [#24 Documentation & Demo Preparation](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/24) | README and Windows setup/foundation documentation exist. | Verify final documentation against the integrated app and confirm required Sprint 1/Sprint 2 demo artifacts are uploaded; no demo evidence was checked in this repository review. |

**Epic status:** Foundation and CI are integrated. End-to-end verification, defect resolution, and demo evidence remain.

## Epic 6 — Quiz Management & Participation (#25)

| Story | Integration on `main` | Remaining for the whole story |
| --- | --- | --- |
| [#26 Create and Configure Quizzes](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/26) | Authenticated quiz creation, question selection, configuration validation, unique room codes, and safe response schemas exist with tests. | Integrate quiz creation UI and verify host permissions and answer-key withholding in the browser. |
| [#27 Participate in Quizzes](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/27) | REST session/join/answer endpoints and live room join/state handling are implemented; backend tests cover authenticated participation and invalid access. | Main frontend has no quiz participation or live-room UI. Integrate it and run student/host browser tests, including invalid/expired room behavior. |
| [#28 Submit and Evaluate Quizzes](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/28) | Server evaluates answers, computes/persists results and attempts, applies access checks, and has REST/realtime tests. | Integrate answer submission and results screens; verify real user flow and answer/explanation visibility timing in the browser. |
| [#29 Real-Time Quiz Updates](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/29) | `/ws/quizzes/{room_code}` supports host start, `QUESTION_OPEN`, 30-second rounds, answer state, `ROUND_END`, reconnect/error handling, and hides keys before evaluation. Tests check broadcast under 150 ms and answer-key withholding. | There is no WebSocket quiz client in the main React app. Verify end-to-end WSS through the TLS proxy and connect the live UI before calling the full story integrated. |

**Epic status:** Backend quiz flows are present; the quiz user interface and complete browser-level integration remain.

## Supporting setup tasks under #20

Issues [#30](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/30), [#32](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/32), [#34](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/34), [#36](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/36), [#38](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/38), [#41](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/41), and [#51](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/issues/51) track pieces of the foundation/CI work. They are tasks, not additional epics or user stories. Their code is represented above by the acceptance areas it supports. Check their individual GitHub state before changing or closing any of them.

## Verification basis and next integration pass

- Repository inspected: `main` at `61487721390175fa9a1bfee80508cbd4cd287106`.
- Baseline command: `python -m pytest -q -rs --cov=app --cov-branch --cov-report=term-missing` from `backend`.
- Actual result: **131 passed, 2 skipped, 87% total coverage**. Skips: `test_materials.py::test_upload_real_storage_round_trip` and `test_storage.py` local S3 tests, each requiring optional storage settings.
- Backend behavior and CI configuration were checked in code; this document does not claim a browser-wide test, storage round trip, TLS run, 600 ms analytics benchmark, or 24-hour availability/soak test.
- Next: reconcile the frontend feature work with current `main`; run browser workflows for each story; append reproducible defects to `docs/bug-report-log.md`; keep fixes for the team's separate fix pass.
