# CSMQP Software Testing & Verification Commands Guide

This document provides the exact, reproducible PowerShell commands to execute all test suites, automated IEEE Std 829 test cases (**TC-01 through TC-12**), performance benchmarks (**NFR-01, NFR-02, NFR-03**), security audits (**SEC-01, SEC-02**), and code coverage analyses as documented in [`SYSTEM_TEST_PLAN_EXECUTION_AND_PERFORMANCE_REPORT.md`](file:///c:/Users/sreej/Downloads/projects/se/collab-study-quiz-platform/SYSTEM_TEST_PLAN_EXECUTION_AND_PERFORMANCE_REPORT.md).

---

## ⚡ Quick Start: Run the Complete IEEE 829 Validation Suite

To run all 12 test cases with automated pass/fail assertions, latency benchmarking, and JSON evidence generation:

```powershell
# Navigate to the backend directory
cd backend

# Execute the automated validation harness
.\.venv\Scripts\python.exe run_test_plan_validation.py
```

### Expected Output Summary:
```text
==========================================================================================
ID      | REQ            | TITLE                                      | TYPE                 | LATENCY    | STATUS
==========================================================================================
TC-01   | FR-01          | Valid User Authentication                  | Functional (Positive)|  199.18 ms | PASS
TC-02   | FR-01          | Invalid Login Rejection                    | Functional (Negative)|  252.73 ms | PASS
TC-03   | FR-02          | Valid Study Material Upload (8.4 MB PDF)   | Functional / Storage |   64.20 ms | PASS
TC-04   | FR-02          | Oversized File Rejection (> 25 MB Constr)  | Boundary / Robustness|  205.92 ms | PASS
TC-05   | FR-03          | Question Bank Topic Filter Query (/quest)  | Functional / Search  |    8.99 ms | PASS
TC-06   | FR-04, NFR-02  | Live Quiz Session Join & Sync Latency (<)  | Real-Time / Perfor   |   26.36 ms | PASS
TC-07   | FR-05          | Score & Accuracy Calculation (7/10 = 70.0%)| Functional / Math    |   16.08 ms | PASS
TC-08   | FR-05, NFR-01  | Analytics Latency Under Load (<= 600 ms)   | Performance / Load   |   28.86 ms | PASS
TC-09   | SEC-01         | Analytics IDOR Cross-User Access Defense   | Security / Auth      |    5.20 ms | PASS
TC-10   | SEC-02         | In-Flight Answer Key Concealment           | Security / Integrity |    6.70 ms | PASS
TC-11   | NFR-03         | Platform Availability & Health Check Probe | Reliability / SLA    |    1.59 ms | PASS
TC-12   | SEC-01         | SQL Injection Defense on Search Fields     | Security / Data      |    1.15 ms | PASS
==========================================================================================
```
*Results and timing metrics are automatically exported to `backend/test_execution_results.json`.*

---

## 1. Environment Setup & Configuration

Load your local development environment variables into your active PowerShell session before running the backend test suites:

```powershell
# From the repository root
Get-Content .env | ForEach-Object {
    if ($_ -match '^[A-Z][A-Z0-9_]*=') {
        $parts = $_ -split '=', 2
        [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
    }
}
```

---

## 2. Full Pytest Backend Suite with Branch Coverage

Runs all 131+ unit and integration tests across the backend application, recording statement coverage, branch coverage, JUnit XML logs, and missing line numbers:

```powershell
cd backend

# Execute pytest with statement and branch coverage
.\.venv\Scripts\python.exe -m pytest -q -rs `
  --cov=app `
  --cov-branch `
  --cov-report=term-missing `
  --cov-report=json:../docs/qa-2026-11-11/coverage.json `
  --junitxml=../docs/qa-2026-11-11/pytest.xml
```

* **Target Output:** `131 passed, 2 skipped in ~99s`
* **Statement Coverage:** `90.64%` (1,240 / 1,368 statements)
* **Combined Branch Coverage:** `86.71%` (rounded to `87%`)

---

## 3. Subsystem & Feature-Specific Test Commands

To test individual modules or user stories in isolation:

### A. Question Bank & Categorization (Stories #11-#13, TC-05)
```powershell
cd backend
# Test question creation, retrieval, filtering, and difficulty categories
.\.venv\Scripts\python.exe -m pytest tests/test_questions.py tests/test_categorization.py tests/test_manage_questions.py -v
```

### B. Question Moderation Workflow (Story #14)
```powershell
cd backend
# Test moderator approval, rejection, and role-based access control
.\.venv\Scripts\python.exe -m pytest tests/test_moderation.py -v
```

### C. Topic-Wise Performance Analytics (Story #18, TC-08, TC-09)
```powershell
cd backend
# Test topic accuracy calculations, subject filtering, and IDOR protection
.\.venv\Scripts\python.exe -m pytest tests/test_topic_performance.py -v
```

### D. Learning Progress Tracking (Story #19, TC-08, TC-09)
```powershell
cd backend
# Test milestone timelines, cumulative metrics, and data isolation
.\.venv\Scripts\python.exe -m pytest tests/test_learning_progress.py -v
```

### E. Performance Dashboard & Attempt History (Story #17, TC-07)
```powershell
cd backend
# Test attempt summaries, scoring calculations, and student attempt histories
.\.venv\Scripts\python.exe -m pytest tests/test_performance_dashboard.py tests/test_attempt_history.py -v
```

### F. Synchronous Live Quiz Rooms & WebSockets (Story #15, Story #16, TC-06, TC-10)
```powershell
cd backend
# Test quiz creation, room codes, live question reveals, and participant sync
.\.venv\Scripts\python.exe -m pytest tests/test_quizzes.py tests/test_quiz_realtime.py tests/test_websocket.py -v
```

### G. Study Material Upload & S3 Storage (Story #7, TC-03, TC-04)
```powershell
cd backend
# Test upload validation, 25MB boundary limits, and S3 metadata indexing
.\.venv\Scripts\python.exe -m pytest tests/test_materials.py -v
```

### H. Authentication & Security (Story #21, TC-01, TC-02, TC-12)
```powershell
cd backend
# Test registration, bcrypt login, JWT expiry, and CORS restrictions
.\.venv\Scripts\python.exe -m pytest tests/test_auth.py tests/test_cors.py -v
```

---

## 4. Live Server Health & Availability Checks (NFR-03)

Ensure the live backend process, PostgreSQL database, and S3 object storage are healthy:

```powershell
# 1. FastAPI process health
curl.exe http://127.0.0.1:8000/health
# Response: {"status":"ok"}

# 2. PostgreSQL database connectivity (SELECT 1 probe)
curl.exe http://127.0.0.1:8000/health/db
# Response: {"status":"ok","database":"connected"}

# 3. RustFS / S3 Object Storage bucket check
curl.exe http://127.0.0.1:8000/health/storage
# Response: {"status":"ok","storage":"connected"}
```

---

## 5. Database Schema & Migration Verification

Verify that all Alembic migrations are up to date and that no schema drift exists:

```powershell
cd backend

# View current database revision head
.\.venv\Scripts\python.exe -m alembic current

# Verify that database schema matches SQLAlchemy models exactly
.\.venv\Scripts\python.exe -m alembic check

# Upgrade database to head if new migrations were added
.\.venv\Scripts\python.exe -m alembic upgrade head
```

---

## 6. Frontend Build & TypeScript Typecheck

Verify the frontend compiles with zero TypeScript errors and builds for production:

```powershell
cd frontend

# Run TypeScript type check and production bundle build
npm.cmd run build
```

---

## 7. Starting the Servers for Local or Live Evaluation

### Terminal 1: Backend Server (Port 8000)
```powershell
# In repo root:
Get-Content .env | ForEach-Object {
    if ($_ -match '^[A-Z][A-Z0-9_]*=') {
        $parts = $_ -split '=', 2
        [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
    }
}
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Terminal 2: Frontend Server (Port 5173, Accessible on LAN & Tunnel)
```powershell
cd frontend
npm.cmd run dev
```

### Terminal 3: Public Internet Live Tunnel (Cloudflare)
```powershell
# In repo root:
.\cloudflared.exe tunnel --url http://localhost:5173
```
*Generates an instant, free public `https://...trycloudflare.com` URL that allows anyone in the world to access the platform on mobile or desktop without configuration.*
