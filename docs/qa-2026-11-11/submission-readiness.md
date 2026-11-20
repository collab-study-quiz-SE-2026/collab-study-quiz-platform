# Submission readiness — 11 November 2026

This records the 11 November verification pass. PR #69 is merged to `main` at `1762d4b`. Current local browser/UI notes and small materials/history UI edits are not committed. This is a presentable interim QA handoff, not a claim that every requirement or story is complete.

Use [submission checklist](../SUBMISSION_CHECKLIST.md) to package deliverables and [viva preparation guide](../VIVA_PREPARATION.md) to study the architecture, features, evidence, and limitations.

## Current implementation

| Area | Implemented | Evidence still needed |
| --- | --- | --- |
| Auth #2–#4 | Registration, login/logout, roles and session restoration; invalid-password error then correct login passed | Actual token-expiry browser recovery |
| Materials #6–#9 | PDF and Markdown upload; invalid upload rejection; other-student download; search/tag/combined filters, clear filters and no-results passed | BUG-001 tags required; BUG-003 card overflow; decide if #8 needs taxonomy administration. Partial text matching is future work |
| Questions #11–#14 | Question category/difficulty filters, creator edit propagation, other-student UI restriction, moderation rejection/status/reason visibility passed | Direct forged cross-user API edit/delete; BUG-004 tiny moderator reason input |
| Analytics/history #16–#19 | Empty and completed history, refreshed overview/topic/progress with two quiz attempts passed | 1,000-attempt latency benchmark and representative cohort evaluation |
| Quiz #26–#29 | Create/join, invalid room rejection, two-student answer/scoring/leaderboard flow, timeout and reconnect/resume passed | Configured quiz duration versus fixed 30-second live rounds needs product decision; WSS latency/soak verification |
| Foundation/QA #21–#24 | Compose, migrations, CI, TLS verifier, test reports and bug log | Final checklist audit and evidence packaging |

## Existing evidence

- Latest regression on 11 November: **133 passed, zero skipped, 1 HTTPX deprecation warning in 81.37 seconds**. Both `RUN_STORAGE_TESTS=1` and `RUN_UPLOAD_INTEGRATION=1` were enabled. PostgreSQL used a new dedicated `csmqp_submission_*` database; RustFS checks uploaded/read/deleted their own temporary objects. JUnit evidence: [submission-pytest.xml](submission-pytest.xml). This supersedes the earlier storage-skip limitation for automated local verification, not browser acceptance. No new coverage percentage was measured.
- GitHub readback after fetch: PR #69 is merged to `main` as `1762d4b`.

- User-reported manual success: student auth and role denial; moderator approval and cross-user question visibility; two-student quiz with leaderboard/history; cross-user PDF upload/download; logout token rejection; TLS 1.3 HTTPS/WSS verifier.
- Earlier automated baseline: 131 passed, 2 optional storage checks skipped. See the existing unit/coverage reports for that exact run.
- Small follow-up: 31 passed, 1 real-storage test deselected; frontend build passed. See `small-story-checks.md`.
- Supplemental user-reported browser results are recorded in `small-story-checks.md` and `../manual-testing-log.md`. The in-app browser could not access localhost, so these are recorded from the user's direct browser observations and supplied screenshots.

## Final packaging order

1. Finish and retest Shubham's BUG-001/003 changes. Fix/retest BUG-004 if time permits.
2. Decide whether the fixed 30-second live round timer is intended or should use quiz configuration; update docs/code only after the expected behavior is agreed.
3. Run the remaining specification checks listed below where time/environment permits; attach measured evidence.
4. Commit and push the local materials/history UI and QA notes, then run CI on that final revision.
5. Check each required deliverable in the submission PDFs and package the final code, setup guide, SRS/SDD/test plan, executed test results, bug/retest log and project evidence in required formats.

## Known limitations to disclose

Planned follow-up rather than claimed complete: actual expired-token recovery; direct backend authorization checks for forged cross-user edit/delete; precise TC-03/04 sample-size browser checks; measured TC-06 <=150 ms and TC-08 <=600 ms/1,000-attempt benchmarks; TC-10 saved quiz-frame inspection; TC-11 24-hour, 50-user soak; endpoint-level TC-12 malicious-input checks; WSS latency/reconnect through TLS; taxonomy requirement decision; and BUG-001/003/004 disposition. Demo recording and deadline dates are excluded at the user's request. Test reports contain earlier exact run counts; latest focused browser notes are user-reported and are not CI artifacts.
