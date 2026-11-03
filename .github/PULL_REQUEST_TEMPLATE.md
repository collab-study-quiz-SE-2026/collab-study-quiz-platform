
## What changed
- Added GitHub Actions CI workflow for backend tests.
- Configured Python 3.12 and PostgreSQL 15.
- Added automated pytest execution.

## Related issue
Closes #22

## How tested
- [ ] Ran backend tests locally using `python -m pytest -q`.
- [ ] Verified dependencies using `python -m pip check`.
- [ ] Verified GitHub Actions CI workflow.

## Review checklist
- [ ] Workflow runs on pushes and pull requests to main.
- [ ] PostgreSQL test database is isolated.
- [ ] No development database credentials are committed.
- [ ] No unrelated application code or migrations were modified.
