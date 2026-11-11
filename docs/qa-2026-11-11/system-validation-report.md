# System validation and test-plan mapping

Run date: 11 November 2026 (IST). Source revision: 8e4abffc0f3e0b1dd3cc79f9556ddc04b507a894.


Source plan is [Software Test Plan & Test Cases v1.0](../CSMQP%20-%20Software%20Test%20Plan%20%26%20Test%20Cases-1.pdf). The full story-level browser pass was deferred by Somesh. A case marked partial has supporting checks but lacks part of its exact specified scenario.

| Case / requirement | Evidence available | Assessment and remaining work |
| --- | --- | --- |
| TC-01 / FR-01 valid authentication | test_auth registration/login/profile cases passed. Somesh previously completed student registration, refresh, logout/relogin and moderator login. | Covered by backend assertions and prior manual flow. Retest normal login after shortcut removal. |
| TC-02 / FR-01 invalid login | test_login_jwt_expiry_and_invalid_credentials passed. | Backend rejection verified. New UI error presentation pending browser check. |
| TC-03 / FR-02 upload | PDF/Markdown success and metadata tests passed with mocked storage. Prior two-student real RustFS upload/download succeeded. | Partial exact-plan evidence. The specified 8.4 MB PDF was not recorded. BUG-001 missing-tag validation is with Shubham. |
| TC-04 / FR-02 oversized upload | test_upload_rejects_file_over_25_mb passed. | Boundary behavior covered. Exact 28 MB sample and browser presentation remain unexecuted in this run. |
| TC-05 / FR-03 filtering | Categorization and question tests passed. Prior subject/topic material filters worked. | Partial. Plan route/course parameter requires the route update below. Full question filter UI combinations deferred. |
| TC-06 / FR-04, NFR-02 live sync | test_live_round_broadcasts_question_and_withholds_key_until_all_answer passed. Prior moderator + two students completed two rounds. | Partial. Exact three-peer browser/network latency scenario at <=150 ms remains unmeasured. |
| TC-07 / FR-05 scoring | Quiz, participation, dashboard and topic calculation assertions passed. Prior live quiz revealed scores and final leaderboard. | Supported functional calculations. Exact 7-correct/3-wrong ten-question browser case still needs evidence. |
| TC-08 / FR-05, NFR-01 analytics latency | Dashboard/topic/progress calculation and privacy tests passed. Fresh live QA account returned 200 with empty responses at all three analytics routes. | Partial. 1,000 attempts and <=600 ms rendering benchmark remain pending. New analytics screens need browser verification with populated data. |
| TC-09 / SEC-01 privacy | Dashboard, topic and progress cross-user access tests passed. Prior manual cross-user request returned 403 but route was not recorded. | Automated access controls verified. Record exact route in next manual check. |
| TC-10 / SEC-02 conceal answers | Realtime payload assertion passed. Prior manual round revealed answer after both participants answered. | Automated payload omission verified. A saved browser-frame inspection remains pending. |
| TC-11 / NFR-03 availability | Health tests passed. | Pending 24-hour/30-second probe run with 50 concurrent users, >=99.5% success and resource/WAL observations. |
| TC-12 / SEC-01 SQL injection | test_sqlalchemy_select_one passed with a malicious-looking value bound as data. | Partial. Endpoint-level malicious search and creation inputs with before/after data checks remain pending. |

## Additional completed evidence

- Fresh migration upgrade and Alembic schema comparison succeeded.
- Backend pytest and coverage evidence are saved alongside this report.
- Local frontend TypeScript compilation and Vite build succeeded.
- A real HTTP API smoke run against the isolated QA database registered a temporary student, logged in, and received 200 from health, dashboard, topic analytics and progress. Credential-free empty payloads are saved in [analytics-api-smoke.json](analytics-api-smoke.json).
- Somesh confirmed authenticated local quiz WSS testing in the handoff correction. Prior verify_tls.py output confirmed certificate verification, TLS 1.3, HTTPS health and WSS health ping/pong, plus TLS 1.2 rejection.
- BUG-002 implementation removes the preset login buttons and account-switch shortcuts and their auto-registration fallback. Registration now occurs through the explicit Create Account form.

## Remaining manual checks for Somesh

Start the app using the setup guide and sign in normally with existing student and moderator accounts. Verify that each account shows its actual role. In Analytics, check Overview, Topic performance and Learning progress with a student who has completed quizzes. Compare one known result, filter a subject, use Refresh, then try a new student with zero attempts. Check the page at a narrow width and navigate chart points with the keyboard. Record screenshots and expected/actual values.

Browser automation attempted localhost:5173 but the in-app browser returned connection errors even after Vite started. UI visual and interaction acceptance is pending. The QA backend used an isolated database. The temporary Vite and backend processes were stopped after checks. Start FastAPI with the usual local environment before checking existing accounts.

Shubham owns BUG-001 and BUG-003. Follow up on his PRs and append retest outcomes. Additional edge-case scenarios remain in the original test plan and integration checklist.
