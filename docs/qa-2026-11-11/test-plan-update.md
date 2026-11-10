# Test plan execution addendum

Run date: 11 November 2026 (IST). Source revision: 8e4abffc0f3e0b1dd3cc79f9556ddc04b507a894.


This addendum updates execution routes for the original v1.0 cases while preserving their acceptance criteria. Use the system validation report for results.

| Original plan route | Implemented route to use |
| --- | --- |
| /api/v1/auth/login | /auth/login |
| /api/v1/questions/search?topic=OS&course=CS301 | /questions?topic=OS with supported subject/difficulty filters. Course is absent from the question schema. Record this design deviation and agree whether subject satisfies the intended category. |
| /api/v1/analytics/performance/me | /dashboard/performance, with /analytics/topics and /analytics/progress for detailed views |
| /api/v1/analytics/performance/UserB_ID | /users/{student_id}/dashboard/performance and corresponding topic/progress private routes |
| /healthz | /health |

Testing tools used here are Pytest/FastAPI TestClient, SQLAlchemy/PostgreSQL, coverage.py, local HTTP requests and reported manual browser runs. Locust/k6 load and soak tests remain pending. Update the final submitted test-plan document with these routes, tooling deviations and the final case outcomes.

Additional UI regression checks cover BUG-002 normal login after shortcut removal and analytics empty/populated/error/refresh/subject-filter states. These remain manual acceptance items. The full story-by-story browser pass is deferred per Somesh's instruction.
