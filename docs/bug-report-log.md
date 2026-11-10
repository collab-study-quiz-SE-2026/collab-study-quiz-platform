# Bug Report Log

Use this log during Member 2 testing and the Member 1 handoff. Record reproducible defects here; do not treat a skipped test, setup issue, or unverified suspicion as a confirmed application bug. Fixes are tracked separately after the team reviews the reports.

## Confirmed defects

Three confirmed issues are recorded for team review. No fixes have been made.

| ID | Test case / requirement | Area / related issue | Severity | Reproducible? | Owner | Status |
| --- | --- | --- | --- | --- | --- | --- |
| BUG-001 | TC-03 / FR-02 / #6 | Study material upload | Medium | Yes | Assigned teammate | Open |
| BUG-002 | TC-01 / FR-01 / #1 | Moderator demo login | Medium | Yes | Unassigned | Open |
| BUG-003 | TC-03 / FR-02 / #7 | Study material card layout | Low | Yes | Assigned teammate | Open |

### BUG-001 — Upload accepts missing tags

- **Area / issue:** Study material upload / #6
- **Test case / requirement:** TC-03 / FR-02
- **Severity:** Medium
- **Environment / revision:** `main` snapshot `5fb37bd` at time of reproduction; local isolated PostgreSQL test database; storage mocked
- **Steps to reproduce:**
  1. Register and log in as a student.
  2. Send an authenticated `POST /materials/upload` with a valid Markdown file, title, and course code, but omit the `tags` form field.
- **Expected:** Reject the upload because Issue #6 requires comma-separated tags for each upload.
- **Actual:** The endpoint returns HTTP 201 and stores the material with an empty tag list (`tags: []`).
- **Evidence:** Reproduced locally; the temporary account and metadata were removed after the check.
- **Owner / next action:** Assigned teammate to implement the fix in the follow-up pass; retest afterward.
- **Status:** Open

### BUG-002 — Moderator quick login can create a student account

- **Area / issue:** Authentication demo shortcut / #1, #3, #4
- **Test case / requirement:** TC-01 / FR-01
- **Severity:** Medium
- **Environment / revision:** Local `codex/reconcile-frontend-full-ui` working branch based on `main` `6148772`
- **Steps to reproduce:**
  1. Use the Moderator Account quick-login shortcut when its preset account is not already a moderator in the local database.
- **Expected:** The shortcut signs in to a moderator account or gives a clear setup instruction.
- **Actual:** On login failure, the quick-login helper attempts registration. Registration always creates a student, so the shortcut can end up signed in as a student instead of a moderator.
- **Evidence:** Reported during local role testing; confirmed in `frontend/src/App.tsx` quick-login fallback and the backend's student-only registration behavior.
- **Owner / next action:** Team to review and decide the fix in the second pass. For testing now, create a normal account and promote it locally in PostgreSQL.
- **Status:** Open

### BUG-003 — Long material title overflows its card

- **Area / issue:** Study material browse card / #7
- **Test case / requirement:** TC-03 / FR-02 (visual layout detail; the supplied test plan has no dedicated layout case)
- **Severity:** Low
- **Environment / revision:** Local `codex/reconcile-frontend-full-ui` working branch; browser screenshot provided during manual test
- **Steps to reproduce:**
  1. Browse a material whose title contains a long unbroken string, such as a filename with underscores.
- **Expected:** The title wraps or otherwise remains within the material card's border.
- **Actual:** The title extends past the card's right border.
- **Evidence:** User-provided screenshot `codex-clipboard-8c49c2f8-c750-437b-ab80-7762077d600b.png`.
- **Owner / next action:** Assigned teammate to implement the fix in the follow-up pass; retest afterward.
- **Status:** Open

## Report template

Copy this section for each confirmed defect.

### BUG-### — Short title

- **Area / issue:**
- **Test case / requirement:**
- **Severity:** Critical / High / Medium / Low
- **Environment / revision:**
- **Steps to reproduce:**
  1.
- **Expected:**
- **Actual:**
- **Evidence:** Test name, command/output, API response, or screenshot
- **Owner / next action:**
- **Status:** Open / Fixing / Retesting / Closed

## Test-case reference index

Source: `CSMQP - Software Test Plan & Test Cases-1.pdf` in this folder. Include the relevant case ID and requirement ID in every bug report. This index is for traceability; it does not mark a test as passed.

| Test case | Requirement | Scenario |
| --- | --- | --- |
| TC-01 | FR-01 | Valid authentication |
| TC-02 | FR-01 | Invalid login rejection |
| TC-03 | FR-02 | Valid material upload and storage |
| TC-04 | FR-02 | Reject oversized material |
| TC-05 | FR-03 | Question Bank filtering |
| TC-06 | FR-04, NFR-02 | Live quiz synchronization latency (150 ms target) |
| TC-07 | FR-05 | Quiz score and accuracy calculation |
| TC-08 | FR-05, NFR-01 | Analytics query latency (600 ms target) |
| TC-09 | SEC-01 | Analytics cross-user access / IDOR protection |
| TC-10 | SEC-02 | Hide answer keys during an active quiz round |
| TC-11 | NFR-03 | 24-hour availability and soak test |
| TC-12 | SEC-01 | SQL injection defenses on search and input fields |

## Environment observations (not confirmed application defects)

- The existing local `csmqp_test` database has a `users` table but is not at a usable Alembic starting revision. Integration checks used the separate `csmqp_story29_test` database instead. Do not reset or drop either database as part of routine testing.
