# QA evidence · 11 November 2026

Baseline source revision 8e4abffc0f3e0b1dd3cc79f9556ddc04b507a894. PR #69 is merged to main as `1762d4b`; supplemental user-reported browser checks and interim readiness status are recorded separately.

- [Unit and backend test report](unit-test-report.md)
- [System validation and TC-01–TC-12 matrix](system-validation-report.md)
- [Code coverage report](code-coverage-report.md)
- [Branch coverage report](branch-coverage-report.md)
- [Test-plan update](test-plan-update.md)

The baseline run recorded 131 tests passed and two optional storage checks skipped. A later full regression run with both storage integrations enabled recorded 133 passed, zero skipped, and one HTTPX deprecation warning; see [submission run](submission-pytest.xml). The 90.64% statement and 72.16% branch coverage figures belong to the earlier baseline run. User-reported browser checks and remaining specification benchmarks are documented in [submission readiness](submission-readiness.md) and [small story checks](small-story-checks.md).
