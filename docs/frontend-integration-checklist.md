> Update, 11 November 2026: The snapshot below is historical. PR #67 integrated the feature screens; the current branch also contains analytics UI and the small materials/history fixes. See [submission readiness](qa-2026-11-11/submission-readiness.md) for current implementation and verification gaps. Do not use the old missing-screen statements as the current backlog.

# Frontend Integration Checklist

Working checklist for integrating `feature/frontend-full-ui` with the latest backend and frontend work. The UI is committed and pushed on `codex/reconcile-frontend-full-ui`; PR #67 is open against `main`. Its frontend build check passed; the backend CI job is blocked by a migration consistency failure also present on the current `main` snapshot. This is a planning document; it does not create or assign GitHub issues.

## Current snapshot (November 10, 2026)

- Latest `main`: `6148772` (`61487721390175fa9a1bfee80508cbd4cd287106`).
- Frontend source branch `origin/feature/frontend-full-ui` is at `269d881` and was merged locally into the reconciliation branch from current `main`.
- The reconciled UI contains login/register/logout, health status, Question Bank, materials upload/browse/download, quiz REST flows, attempt history, and a moderator queue.
- PR #62, which added the backend real-time quiz support, is merged into `main`.
- Latest `main` contains `LearningProgressChart.tsx`, but it is not wired into the main App. The full UI branch does not contain it, so a naive merge would remove that component.
- Latest `main` exposes analytics endpoints for topic performance, progress, and the performance dashboard. The full UI branch has no integrated analytics navigation/screens.
- The full UI branch has no quiz-room WebSocket client. It currently uses REST quiz flows; live quiz UI depends on backend PR #62.

## Checklist

### Integrate the branch safely

- [x] Bring the full UI branch into a new branch from latest `main`; Git merged automatically without conflicts and preserved `LearningProgressChart.tsx`.
- [x] Open a frontend PR against `main`; keep it separate from backend PR #62. PR #67 is open.
- [x] Confirm the frontend build passes after integration (`npm run build`).

### Align the frontend with current API responses

- [x] Align `StudyMaterial` type/rendering with backend fields `original_filename`, `file_size`, `file_type`, `mime_type`, and `created_at`; public responses do not include `storage_key`.
- [x] Align the moderator UI status comparison with lowercase API values (`pending`, `approved`, `rejected`).
- [x] Remove the unused question search helper that sent a `q` parameter the current backend does not accept. The Question Bank uses supported subject/topic/difficulty filters.
- [ ] Check every API helper and form against the latest backend routes, required fields, response shapes, and error responses.
- [ ] Verify and report missing-tags behavior against BUG-001; decide on frontend/backend handling during the follow-up fix pass.
- [ ] Review and report the hard-coded quick-demo account credentials in `App.tsx`; do not add or distribute real credentials.

### Complete existing feature screens

- [ ] Question Bank: verify create, personal list, browse, edit/delete, category filters, and useful text search.
- [ ] Moderation: verify moderator-only queue, approve/reject actions, and refresh after an action.
- [ ] Study materials: verify upload, required metadata, filters, listing, and byte-correct downloads with real local services.
- [ ] Quiz REST flow: verify quiz creation, room-code join, participation, answer submission, evaluation, and result display.
- [ ] Attempt history: verify completed/expired results, empty state, refresh, and score/time display.

### Add the missing analytics and live-quiz UI

- [ ] Wire the existing `LearningProgressChart` into the authenticated app and confirm its `/analytics/progress` request and empty/error states.
- [ ] Add a performance dashboard screen for issue #17 using `/dashboard/performance`.
- [ ] Add topic-wise performance screen/filter for issue #18 using `/analytics/topics`.
- [x] Add the live quiz room client for issue #29: authenticated WebSocket connection, host start, `QUESTION_OPEN`, countdown, answer submission/state, `ROUND_END`, reconnect/error handling, and delayed answer-key display. Backend support is on `main` through PR #62.
- [ ] End-to-end verify the host and participant browser flow against the local backend, including multiple participants, timeout, reconnect, and the TLS proxy.
- [ ] Ensure students and moderators see only the views/actions allowed by their role.

### Finish with a manual browser pass

- [ ] Check loading, empty, success, validation, and server-error states for each screen.
- [ ] Check keyboard navigation, labels, readable error messages, and narrow-screen layout.
- [ ] Verify login, refresh/session restoration, logout, expired-token behavior, and backend-unavailable recovery.
- [ ] Record any reproducible defects in `docs/bug-report-log.md`, citing relevant test case IDs from the test plan. Do not fix defects during the reporting pass.

## Suggested two-person split

### Person 1 — integration, shared API, questions, and materials

- Complete UI/API reconciliation, then open the frontend PR.
- Own shared `App.tsx`, `api.ts`, and `types.ts` changes to avoid competing edits.
- Audit API contracts, Question Bank, moderation, materials, and demo-login behavior; record reproducible defects with test-case IDs.
- Keep implementation fixes for the later team-approved pass.

### Person 2 — quizzes, history, analytics, and live rooms

- Audit `Quizzes.tsx` and `AttemptHistory.tsx` against the latest APIs and test cases; report reproducible defects.
- Identify missing progress/dashboard/topic-performance screens and outline the UI/API pieces needed.
- Verify backend WSS and add the live quiz client in its separately agreed feature scope.
- Coordinate any shared API helper/type needs with Person 1 before changing shared files.
- Record frontend defects in the same bug log; do not fix them in the reporting pass.

## Coordination rule

Person 1 owns the shared app shell, API helpers, and shared TypeScript types. Person 2 should request additions to those interfaces rather than editing the same files in parallel. Keep implementation fixes for a separate pass after the team reviews the bug log.
