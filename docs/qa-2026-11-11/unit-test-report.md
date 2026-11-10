# Unit and backend test execution report

Run date: 11 November 2026 (IST). Source revision: 8e4abffc0f3e0b1dd3cc79f9556ddc04b507a894.

The backend suite completed with **131 passed, 2 skipped and zero failures** in 99.82 seconds. It includes schema unit tests, API integration tests, database checks and WebSocket tests. SQLite fixtures and dedicated PostgreSQL databases isolate test data. The app and test database names differ. The development database was preserved.

Python 3.12.14 and the repository virtual environment were used. Fresh PostgreSQL 15 migration verification reached 20261110_0006 and reported no new upgrade operations. One FastAPI/Starlette HTTPX deprecation warning appeared.

The optional real-storage tests were skipped because RUN_UPLOAD_INTEGRATION and RUN_STORAGE_TESTS were unset. The prior manual PDF round trip supplies separate system evidence.

Executed from backend/ with PostgreSQL environment and TEST_PGDATABASE configured:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -rs --cov=app --cov-branch --cov-report=term-missing --cov-report=json:../docs/qa-2026-11-11/coverage.json --junitxml=../docs/qa-2026-11-11/pytest.xml
```

Raw evidence is in [pytest.xml](pytest.xml) and [pytest-output.txt](pytest-output.txt). Frontend production compilation/build also passed. Frontend browser regression checks remain pending because the in-app browser could not connect to the local Vite server.

| Test group | Passed | Skipped | Failed/error |
| --- | ---: | ---: | ---: |
| test_quiz_schema | 16 | 0 | 0 |
| tests.test_attempt_history | 2 | 0 | 0 |
| tests.test_auth | 3 | 0 | 0 |
| tests.test_categorization | 7 | 0 | 0 |
| tests.test_cors | 3 | 0 | 0 |
| tests.test_database | 2 | 0 | 0 |
| tests.test_health | 1 | 0 | 0 |
| tests.test_learning_progress | 4 | 0 | 0 |
| tests.test_manage_questions | 7 | 0 | 0 |
| tests.test_materials | 26 | 1 | 0 |
| tests.test_moderation | 9 | 0 | 0 |
| tests.test_participation | 5 | 0 | 0 |
| tests.test_performance_dashboard | 2 | 0 | 0 |
| tests.test_question_schema | 9 | 0 | 0 |
| tests.test_questions | 16 | 0 | 0 |
| tests.test_quiz_realtime | 4 | 0 | 0 |
| tests.test_quizzes | 3 | 0 | 0 |
| tests.test_sqlalchemy | 1 | 0 | 0 |
| tests.test_storage | 2 | 1 | 0 |
| tests.test_topic_performance | 5 | 0 | 0 |
| tests.test_websocket | 4 | 0 | 0 |
