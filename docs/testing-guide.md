
# Backend Testing Guide

## 1. Prerequisites

Before running backend tests, make sure you have:

- Python 3.12 installed.
- Git installed.
- Access to the project repository.

PostgreSQL 15 is required for database integration tests.

## 2. Set up the Python environment

From the repository root, run:

```bash
python3.12 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

## 3. Configure test environment variables

Set the PostgreSQL environment variables:

```bash
export PGUSER=ci_test
export PGPASSWORD=ci_only_password
export PGHOST=127.0.0.1
export PGPORT=5432
export PGDATABASE=csmqp_dev
export TEST_PGDATABASE=csmqp_test
export JWT_SECRET_KEY=test-only-secret
export FRONTEND_ORIGIN=http://localhost:5173,https://localhost
```

These are example test-only values. Do not use production credentials.

## 4. Run backend tests

Navigate to the backend directory:

```bash
cd backend
```

Run all backend tests:

```bash
python -m pytest -v
```

For a concise test summary:

```bash
python -m pytest -q
```

Check installed dependencies:

```bash
python -m pip check
```

## 5. Database integration tests

Some tests require a dedicated PostgreSQL test database.

Make sure PostgreSQL is running and that both the development database and the separate test database exist.

The test database must be different from the development database.

Do not point TEST_PGDATABASE to a production or development database.

## 6. GitHub Actions CI

The backend CI workflow is located at:

`.github/workflows/ci.yml`

It runs when:

- Code is pushed to the main branch.
- A pull request is opened or updated against main.

The workflow:

1. Checks out the repository.
2. Sets up Python 3.12.
3. Starts an isolated PostgreSQL 15 service.
4. Installs backend dependencies.
5. Creates a dedicated test database.
6. Runs the backend pytest suite.

## 7. Troubleshooting

### Python version error

Check your Python version:

```bash
python --version
```

Use Python 3.12 for this project.

### Missing dependencies

Run:

```bash
python -m pip install -r requirements.txt
```

### PostgreSQL connection failure

Check that PostgreSQL is running and verify:

- PGHOST
- PGPORT
- PGUSER
- PGPASSWORD
- PGDATABASE
- TEST_PGDATABASE

Ensure the dedicated test database exists.

### Tests are skipped

Some integration tests skip when TEST_PGDATABASE is not configured.

Set TEST_PGDATABASE to an existing dedicated test database.

### GitHub Actions failure

Open the failed workflow run in the repository's Actions tab.

Check the failing step's logs, identify the error, fix the issue, and push the changes again.

## 8. Important safety guidelines

- Never commit real database passwords or API secrets.
- Never run integration tests against a production database.
- Use an isolated test database.
- Do not modify application or migration files as part of the CI setup task.
