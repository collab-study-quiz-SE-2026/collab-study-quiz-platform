# Small story checks — 11 November 2026

Scope: a low-risk subset of the remaining story coverage, as requested. These changes are on `feature/member2-auth-analytics-testing`. This is not full browser acceptance.

## Implemented

- Materials #7–#9: expose the existing API's tag filter alongside subject/topic/search; add Clear filters and explain exact-match versus partial-search behavior. No taxonomy administration has been added.
- Materials: distinguish an empty collection from a search with no matches. Failed requests show an error and Retry rather than claiming the collection is empty. Ignore older search responses when newer filters have been requested.
- History #16: clear old errors when refreshing, disable Refresh during loading, and avoid displaying an empty-history message when the request failed. Display a recorded zero-second duration as `0s` rather than missing data.
- Backend behavior, development records and storage objects were not changed. BUG-001 (required upload tags) and BUG-003 (card overflow) remain assigned to Shubham.

## Executed checks

`npm run build` in frontend: PASS (TypeScript and Vite).

In backend, with PG connection variables and a newly created, dedicated TEST_PGDATABASE:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_auth.py tests/test_materials.py tests/test_attempt_history.py -q -k 'not real_storage_round_trip'
```

Result: **31 passed, 1 deselected, 1 warning in 26.45 seconds**. The warning is the existing HTTPX TestClient deprecation warning. The isolated test database was retained; no development database or Docker volume was deleted.

Coverage includes invalid credentials, JWT expiry-field configuration, logout invalidation, valid Markdown, empty/oversized/malformed PDF rejection, combined category filters, no search results, completed history and cross-user history privacy. Material storage is mocked in this run. The real-storage round trip was deliberately deselected. The auth test verifies token expiry metadata; it does not establish a browser's recovery after an actually expired token.

`git diff --check`: PASS.

## Browser result reported by user

For Materials #9, the user confirmed in the browser that a material appears when search, subject, topic, and tag filters are combined with matching values; tag filtering works; and clearing filters restores all uploaded files. Subject/topic/tag filtering currently needs exact values. The user accepts this for the current submission and wants partial matching recorded as future work. No failure was observed. This is a user-reported manual result, not an independently captured browser session.

The original test plan has no separate test case for material filtering: TC-05 is question search. This check maps to GitHub Story #9 and is also represented by the automated material filter/no-results tests. It should be recorded as a story-level supplemental browser check, rather than mislabeled as TC-05.

For Attempt History #16, the user confirmed that a quiz completed yesterday appears with the correct score and completion time. Mark this completed-attempt display check **PASS (user-reported)**. The empty-history state remains untested.

For Analytics #17–#19, the screenshots provided by the user show populated Overview, Topic performance, and Learning progress views for one completed quiz (50% score; Database Systems topic). The user refreshed and reported that the screens continued to work; no values changed because no new quiz data had been added. Mark these populated-screen and refresh checks **PASS (user-reported)**. The screenshots show a one-attempt sample, so the percentile/trend values are only a basic smoke check, not a meaningful cohort or trend validation. No screenshot files have been copied into the repository.

The user then completed a second quiz on the same topic and supplied screenshots showing the refresh updated all three analytics views: overview changed to 2 attempts and 75% average, listed both results (50% and 100%), and showed topic accuracy 3/4 (75%); topic performance showed 2 quizzes/4 questions and strong; learning progress showed two points, an improving trend, 75% average, and +50 points. Attempt History also showed both completed quizzes with scores and completion times. Mark this refresh-after-new-data check **PASS (user-reported with screenshots)**. Percentile remains a small-sample measure and is not treated as performance benchmarking.

For Auth #3, the user tried an incorrect password, then the correct password without refreshing. The error appeared for the incorrect credentials and the correct login succeeded. Mark invalid-credentials recovery **PASS (user-reported)**. This does not test actual token expiration.

For Materials #9, the user searched for a nonexistent material and confirmed the UI displayed the no-match guidance (“No materials match your filters. Try different values or clear the filters.”). Mark no-results feedback **PASS (user-reported)**. Together with the prior matching, tag, combined-filter and clear-filter checks, the browser smoke coverage for the materials filter UI is complete for this pass.

For Attempt History #16, the user opened history for a student with no attempts and confirmed the “No quiz attempts yet, join a quiz…” empty-state guidance. Mark the empty-history check **PASS (user-reported)**. Combined with the earlier completed-history check, both basic history display states have been exercised.

For Question Bank #13, the user created a test question and confirmed that subject, topic and difficulty filters return it when values match and show no-match feedback when values do not match. Mark the filter-combination check **PASS (user-reported)**. Ownership/edit/delete and moderator rejection remain unverified in this browser pass.

For Question Bank #12, the user confirmed the creator can edit their test question, the edit appears in moderator and second-student views, and a different student does not see edit/delete controls for it. Mark creator edit propagation and absence of unauthorized controls **PASS (user-reported)**. This is a UI check; it does not by itself prove the backend rejects a manually forged cross-user edit/delete request.

For Quiz #26–#29, the user confirmed quiz creation and valid joining work, an invalid room code is rejected with a “No room found” message, and the host's send-question action starts the question immediately. Combined with the earlier two-student live quiz report (waited for both answers, score/reveal, host advance, final leaderboard and attempts in history), mark this local quiz smoke flow **PASS (user-reported)**. Timeout and reconnect edge cases remain unverified.

For Materials #6, the user confirmed a valid Markdown upload works alongside the earlier PDF upload. They also clarified that the “invalid upload” was rejected, as expected (the type/content was not specified). Mark valid Markdown and the reported invalid-file rejection **PASS (user-reported)**; no new defect is filed.

For Quiz #29 timeout, the user left a student unanswered through the round timeout and confirmed the student received 0% for that question. The host then waited to send the second question. Mark timeout scoring **PASS (user-reported)**; host-controlled progression to the next question is consistent with the observed flow.

The user confirmed a disconnected student can re-enter the room with the room key and resume at the current quiz stage. Mark reconnect/resume **PASS (user-reported)**. They also observed that each live question remains limited to 30 seconds even when a quiz duration is configured. This matches the current implementation and `docs/REALTIME_QUIZ.md` (`ROUND_SECONDS = 30`); the configured `duration_minutes` is separately used as the overall REST attempt limit. Whether the live round duration should follow quiz configuration is an unresolved requirements question, not a confirmed code defect.

For Moderation #14, the user confirmed the rejection flow works. They also reported that the moderator message box is too small to read the message comfortably. The workflow is recorded as passed with usability defect BUG-004 open; see `docs/bug-report-log.md` for details.

The user further confirmed the rejected question appears with Rejected status in its creator's My Questions list, the creator can read the rejection reason, and a second student's public Question Bank does not show the rejected question. Mark rejection status, feedback visibility and public-visibility behavior **PASS (user-reported)**. BUG-004 is limited to the moderator message box being too small while composing the reason.

## Other short browser acceptance still required

These checks are instructions, not claimed results:

1. Log in normally. In Materials, enter a known full tag. Combine it with the material's exact subject/topic; confirm the expected record remains. Use a nonexistent tag; confirm the no-match message. Clear filters and confirm records return.
2. Open history with a new student: confirm the empty message. With a student who completed a quiz: confirm results remain visible.
3. Temporarily use browser DevTools Offline, then Refresh history: confirm an error without a misleading empty message. Restore network and Refresh: confirm the old error disappears. Restore network before continuing other testing.
4. Submit an incorrect login password, then the correct one: confirm the error and successful recovery.

## Deferred

Question edit/delete ownership, moderation reject flow, question filter combinations, taxonomy-management interpretation for #8, actual token-expiry recovery, invalid/expired room behavior, timeout/reconnect and expired-attempt display remain outside this small pass. No completion claim is made for those story-level browser cases.
