# Collaborative Study Material & Quiz Platform (CSMQP)
## Comprehensive Viva & Oral Defense Preparation Guide

---

## 1. Executive Project Overview

### 1.1 Project Objective & Problem Statement
The **Collaborative Study Material & Quiz Platform (CSMQP)** is a full-stack academic platform engineered for collaborative learning, structured knowledge assessment, and peer-to-peer educational resource sharing. 

In traditional academic environments, study materials and quiz preparation are fragmented across unorganized cloud folders, chat groups, and disconnected exam portals. CSMQP unifies these domains into a cohesive, secure, and performant web platform featuring:
- **Peer-to-Peer Study Material Exchange:** Authenticated upload, tagging, categorization, and streaming downloads of academic resources (PDF, Markdown).
- **Curated Question Bank & Moderation:** Student-authored question submissions vetted by moderators through an approval workflow to maintain academic integrity.
- **Multi-Mode Quiz Participation:** Synchronous real-time quiz rooms and asynchronous scheduled assessments with automated scoring and timing logs.
- **Deep Performance Analytics:** Topic-wise accuracy breakdowns, per-topic question timing, cohort percentile rankings, and longitudinal score trajectories.
- **Enterprise-Grade Security & RBAC:** Multi-tenant role separation (`student` vs `moderator`), bcrypt password hashing, stateless JWT authentication, and strict server-side authorization.

### 1.2 System Architecture & Tech Stack

```
                     +--------------------------------------------+
                     |         React 19 + TypeScript Frontend     |
                     |         (Vite, Component Modular UI)       |
                     +--------------------------------------------+
                                  |                  |
                         REST API | HTTP        WSS  | WebSockets
                                  v                  v
                     +--------------------------------------------+
                     |            FastAPI ASGI Backend            |
                     |  - Uvicorn Async Server                    |
                     |  - Pydantic v2 Schema Validation           |
                     |  - JWT Stateless Auth & RBAC Middleware    |
                     |  - WebSocket Room Connection Manager       |
                     +--------------------------------------------+
                                  |                  |
                      SQLAlchemy  | Eager-Load  S3   | Boto3
                      Async/Sync  | Sessions    API  | Streaming
                                  v                  v
                     +--------------------+  +--------------------+
                     | PostgreSQL 16 DB   |  | S3-Compatible Blob |
                     | (Relational Store) |  | (MinIO / AWS S3)   |
                     | Alembic Migrations |  | Study File Storage |
                     +--------------------+  +--------------------+
```

#### Technology Justification:
1. **Backend — FastAPI (Python 3.12+):**
   - High performance, ASGI asynchronous request handling.
   - Automatic OpenAPI (Swagger) schema generation.
   - Pydantic v2 integration for strict runtime type enforcement and fast C-based parsing.
2. **Database — PostgreSQL 16 & SQLAlchemy 2.0:**
   - ACID-compliant relational data modeling.
   - Declarative mapped columns (`Mapped[int]`, `Mapped[str]`).
   - Query latency optimization via `selectinload` to eliminate $N+1$ query overhead ($<600\text{ ms}$ under 1,000 attempts, NFR-01).
   - Alembic version-controlled database schema migrations.
3. **Storage — S3-Compatible Object Store (MinIO / AWS S3):**
   - Decoupled blob storage from relational database.
   - Streaming downloads prevent server memory exhaustion when serving large PDFs.
4. **Frontend — React 19 + TypeScript + Vite:**
   - Strict TypeScript compile checks (`tsc --noEmit`).
   - Fast Hot Module Replacement (HMR).
   - Zero-external-dependency interactive SVG charting for longitudinal learning analytics.

---

## 2. Individual Contributions Breakdown

| Team Member | Core Functional Domain | Primary Stories / Issues Owned | Key Modules & Files |
| :--- | :--- | :--- | :--- |
| **Sreejith S** (`sreejith1911`) | **Question Bank Engine, Moderation Workflow, Topic Analytics & Progress Visualization** | **Stories #11, #12, #13, #14, #18, #19** (Sprint 1 & 2) | `backend/app/main.py`, `backend/app/models.py` (`Question`), `schemas.py`, `test_topic_performance.py`, `test_learning_progress.py`, `frontend/src/components/LearningProgressChart.tsx` |
| **Somesh Sudhan S** (`ssoommeesshh`) | **Frontend Architecture & Integration, Authentication, RBAC, Real-Time WebSockets & CI/CD** | **Stories #2, #21, #28, #29, #36** + PR #37, #67, #69 | `frontend/src/App.tsx`, `frontend/src/components/*`, `backend/app/auth.py`, `backend/app/quiz_realtime.py`, `.github/workflows/*` |
| **Soumik Sinha** (`SoumikSinha`) | **Quiz Creation & Configuration, Participation Sessions, Attempt History, Performance Dashboard** | **Stories #16, #26, #27, #17** (Sprint 1 & 2) | `backend/app/models.py` (`Quiz`, `QuizAttempt`), `test_quizzes.py`, `test_participation.py`, `test_performance_dashboard.py` |
| **Shubham Singh** (`shubhammsingh75`) | **Study Material Management, S3 Storage Engine, Metadata Categorization & Search** | **Stories #6, #7, #8** (Sprint 1) | `backend/app/models.py` (`StudyMaterial`), `backend/app/storage.py`, `test_materials.py`, `alembic/versions/*materials*` |

---

### 2.1 Detailed Section: Sreejith S (`sreejith1911`)

#### Functional Responsibilities:
1. **Question Bank Engine (Story #11):**
   - Engineered the `Question` data model and schema validation.
   - Enforced 4-option multiple-choice structure with exact single-choice `correct_answer_index` ($0 \le \text{index} < 4$).
   - Normalized text fields (stripping leading/trailing whitespace, blank text rejection).
2. **Question Management & Author Ownership (Story #12):**
   - Implemented personal question retrieval (`GET /questions/me`), update (`PUT /questions/{id}`), and soft deletion.
   - Enforced strict author isolation: students can only modify or delete their own unapproved/draft questions.
3. **Question Categorization & Subject Taxonomy (Story #13):**
   - Added `subject` and `topic` categorization with composite database indexes (`ix_questions_subject`, `ix_questions_topic`) for high-speed indexing.
   - Implemented category summary counts (`GET /questions/categories`).
4. **Moderation Workflow & State Machine (Story #14):**
   - Designed the `QuestionStatus` enum: `PENDING`, `APPROVED`, `REJECTED`.
   - Built the moderator review queue (`GET /moderation/questions`).
   - Implemented moderation decision endpoints (`POST /questions/{id}/approve`, `POST /questions/{id}/reject`) with optional moderator comments and audit logging (`moderator_id`, `moderated_at`).
   - **Crucial Security Feature:** Automatically filtered public question endpoints (`GET /questions`) to only expose `APPROVED` questions, hiding pending/rejected questions from unauthorized students.
5. **Topic-Wise Performance Analytics (Story #18):**
   - Developed `GET /analytics/topics` and `GET /users/{id}/analytics/topics`.
   - Evaluated completed attempts to calculate topic-wise accuracy percentage: $\frac{\text{Correct}}{\text{Total}} \times 100$.
   - Computed topic-specific average time per question using persisted `question_timings`.
   - Engineered **Cohort Percentile Ranking** comparing student topic accuracy against peer students.
   - Built automatic strength classification: `strong` ($\ge 75\%$), `moderate` ($50\text{--}74.9\%$), and `weak` ($< 50\%$) with `strong_topics` and `weak_topics` lists.
6. **Learning Progress Visualization Engine (Story #19):**
   - Developed `GET /analytics/progress` and interactive SVG chart component `LearningProgressChart.tsx` in React 19.
   - Computed longitudinal score timeline, cumulative moving average, and attempt trajectory (`improving`, `declining`, `stable`).
   - Tracked longitudinal topic trends over time.
7. **Frontend Contribution & Demo Assembly:**
   - Authored the zero-dependency, responsive SVG learning progress chart component (`LearningProgressChart.tsx`) for Story #19.
   - Assembled and validated the local UI forms on `feature/frontend-full-ui` for video evaluation and sprint demonstrations.

---

### 2.2 Detailed Section: Somesh Sudhan S (`ssoommeesshh`)

#### Functional Responsibilities:
1. **Frontend Architecture & Integration Lead (Stories #21, #36, PR #37, PR #67, PR #69):**
   - Built the initial React 19 + TypeScript + Vite frontend architecture and health connection checks (PR #37).
   - Created the authentication UI (login & register forms, JWT session storage in PR #44).
   - Led the full frontend reconciliation and integration into `main` (PR #67), incorporating live WebSocket quiz room flows, and added the Analytics tab and QA test validation evidence (PR #69).
2. **Authentication & Identity Management (Story #2):**
   - Password hashing with `bcrypt` (12 rounds) preventing rainbow table attacks.
   - Stateless JWT tokens (JSON Web Tokens) encoded with user ID, role, and expiration timestamp using `PyJWT` / `passlib`.
   - Token revocation handling via `token_version` tracking.
3. **Role-Based Access Control (RBAC):**
   - Enforced user roles: `student` vs `moderator`.
   - Built FastAPI dependency injection guards (`get_current_user`, `require_role`) preventing unauthorized privilege escalation.
4. **Quiz Submission & Evaluation Engine (Story #28):**
   - Implemented quiz session completion and auto-scoring (`POST /quiz-sessions/{id}/complete`).
   - Persisted `correct_answer_count`, calculated overall percentage `score`, and recorded `AttemptStatus.COMPLETED` or `AttemptStatus.EXPIRED`.
5. **Real-Time WebSocket Quiz Rooms (Story #29):**
   - Engineered asynchronous WebSocket room manager (`quiz_realtime.py`).
   - Managed bidirectional live connections for multi-participant rooms.
   - Broadcast participant joins, answers, and room status updates in real-time.
6. **DevOps & CI/CD Pipelines:**
   - Configured GitHub Actions workflows (`backend-ci.yml`, `ci-frontend-migrations.yml`).
   - Automated Pytest test execution, Alembic head verification, and frontend TypeScript build verification on every Pull Request.

---

### 2.3 Detailed Section: Soumik Sinha (`SoumikSinha`)

#### Functional Responsibilities:
1. **Quiz Creation & Configuration (Story #26):**
   - Implemented `Quiz` model with room code generation (unique 6-character alphanumeric code).
   - Built `QuizQuestion` association table managing question ordering (`position`) and quiz links.
   - Enforced quiz parameters: `duration_minutes`, `max_attempts`, status transitions (`DRAFT` $\to$ `PUBLISHED` $\to$ `LIVE` $\to$ `COMPLETED`).
2. **Quiz Participation Sessions (Story #27):**
   - Built room join endpoint (`POST /quizzes/join/{room_code}`).
   - Created active `QuizAttempt` sessions.
   - Implemented answer submission endpoint (`POST /quiz-sessions/{id}/answers`) recording selected answer indices and per-question timings in JSON payloads (`question_timings`).
3. **Quiz Attempt History (Story #16):**
   - Implemented `GET /quiz-attempts/me` allowing students to inspect previous attempts, scores, and durations.
   - Enforced student attempt isolation (students cannot see other students' attempt logs).
4. **Performance Dashboard (Story #17):**
   - Implemented `GET /dashboard/performance` returning aggregate student KPIs: total quizzes attempted, overall average score, average time per question, recent results, and score trend.
   - Provided clean empty-state response when students have zero attempts.

---

### 2.4 Detailed Section: Shubham Singh (`shubhammsingh75`)

#### Functional Responsibilities:
1. **Study Material Upload Engine (Story #6):**
   - Built `POST /materials/upload` accepting `multipart/form-data`.
   - Enforced permitted file formats: PDF (`application/pdf`) and Markdown (`text/markdown`).
   - Implemented file size validation and UUID-based object naming to prevent file name collisions.
2. **S3 Object Storage Integration:**
   - Implemented Boto3 S3 client wrapper (`backend/app/storage.py`) connecting to S3/MinIO.
   - Ensured atomic uploads: database record creation with rollback and S3 object deletion on failure.
3. **Material Browsing & Search (Stories #7, #8):**
   - Implemented `GET /materials` supporting multiple query filters: `course_code`, `subject`, `topic`, `tag`, and free-text `search`.
   - Built case-insensitive search matching against titles, course codes, and tags.
4. **Streaming File Download Engine:**
   - Built `GET /materials/{id}/download`.
   - Implemented streaming response from S3 avoiding reading large binary files into RAM.
   - Sanitized `Content-Disposition` header with RFC 5987 UTF-8 encoded file names.

---

## 3. High-Yield Viva Questions & Answers

### 3.1 Project Architecture & General Software Engineering Questions

#### Q1: Explain the overall architectural pattern of your application.
**Answer:**
CSMQP follows a decoupled, three-tier micro-service-ready architecture:
1. **Presentation Tier:** Single Page Application (SPA) built with React 19, TypeScript, and Vite.
2. **Application Tier:** Asynchronous REST & WebSocket server using FastAPI on Uvicorn ASGI. Business logic is organized into declarative Pydantic schemas, dependency-injected services, and authentication middlewares.
3. **Data Tier:** Relational persistence with PostgreSQL 16 (managed via SQLAlchemy 2 and Alembic migrations) and binary object storage with an S3-compatible store (MinIO/AWS S3).

#### Q2: Why did you choose FastAPI over Flask or Django?
**Answer:**
- **Asynchronous Concurrency:** Native Python `async`/`await` support on ASGI, essential for handling high-concurrency WebSocket quiz rooms (Story #29).
- **Type Safety & Automatic Validation:** Deep integration with Pydantic v2 validates request bodies at the serialization boundary using Rust-based parsing, eliminating boilerplate input validation.
- **Auto-Documentation:** Built-in OpenAPI and Swagger UI generation without third-party plugins.
- **Lightweight & Modular:** Unlike Django’s heavy monolithic structure, FastAPI allows clean decoupling of database ORM and storage layers.

#### Q3: How do you prevent SQL Injection and Cross-Site Scripting (XSS)?
**Answer:**
- **SQL Injection:** We use SQLAlchemy 2 Core and ORM parameterized queries (`select(...)`). Raw string concatenation is strictly prohibited. All user inputs are treated as data parameters, never executable SQL tokens.
- **XSS:** React automatically escapes string variables before rendering them into the Virtual DOM (treating content as strings rather than executable HTML). Furthermore, our backend returns `Content-Type: application/json` and `X-Content-Type-Options: nosniff`.

#### Q4: How is database migration handled in a team environment? What happens if two developers create migrations concurrently?
**Answer:**
We use **Alembic**. Each migration script defines `revision` and `down_revision`.
If two developers branch off the same base, Alembic develops **multiple heads**.
Alembic will detect this and refuse to run `alembic upgrade head`, throwing an error.
To resolve this, we use merge migrations (e.g. `alembic merge heads -m "merge heads"`) or update the `down_revision` to point sequentially to the preceding head, maintaining a linear or clean DAG migration history. We verified this in PR #63!

---

### 3.2 Sreejith's Domain: Questions, Moderation & Advanced Analytics

#### Q5: Exactly which parts of the project did you build, and who built the frontend?
**Answer:**
My primary engineering domain was the backend **Question Bank & Moderation Subsystem** (Stories #11, #12, #13, #14) and the **Advanced Performance Analytics & Progress Engines** (Stories #18 and #19).
For the frontend, **Somesh Sudhan S** was the lead frontend integrator on GitHub (PR #37 React foundation, PR #44 Auth UI, PR #67 full UI reconciliation with live quiz rooms, and PR #69 Analytics UI).
My specific frontend contribution was authoring the zero-dependency interactive SVG chart component (`LearningProgressChart.tsx`) for Story #19, and assembling the local UI forms on `feature/frontend-full-ui` for the Sprint 1 video demonstration.

#### Q6: How is the Question data model structured, and why did you store options as JSON?
**Answer:**
The `Question` model has `id`, `question_text`, `options` (JSON array of 4 strings), `correct_answer_index` (integer 0-3), `subject`, `topic`, `difficulty`, `creator_id`, `status` (`QuestionStatus`), and moderation audit columns.
We used a JSON column for `options` because:
- Multiple-choice options for a question are tightly bound, read together, and never queried independently (e.g., we never query "Find all questions where Option B is 'Paris'").
- It avoids unnecessary table joins and foreign key lookups on a separate `question_options` table, significantly speeding up quiz generation and retrieval.

#### Q6: How does the Question Moderation workflow protect exam integrity?
**Answer:**
When a student creates a question, its initial state is `QuestionStatus.PENDING`.
- In `GET /questions` (public bank), the query explicitly filters `.where(Question.status == QuestionStatus.APPROVED)`.
- Even if an attacker knows the `question_id` of a pending or rejected question, public access is rejected.
- Only moderators can access `GET /moderation/questions` and call `/questions/{id}/approve` or `/reject`.
- When an author edits an already approved question (`PUT /questions/{id}`), the status is automatically reset to `PENDING` to prevent authors from sneaking in invalid or malicious edits after initial approval.

#### Q7: How does your Topic-Wise Performance Analytics (Story #18) satisfy NFR-01 (< 600 ms latency for 1,000 attempts)?
**Answer:**
We completely eliminated the $N+1$ query problem using SQLAlchemy's `selectinload`:
```python
attempts = db.scalars(
    select(QuizAttempt)
    .options(
        selectinload(QuizAttempt.quiz)
        .selectinload(Quiz.questions)
        .selectinload(QuizQuestion.question)
    )
    .where(QuizAttempt.student_id == student_id, QuizAttempt.status == AttemptStatus.COMPLETED)
).all()
```
Instead of executing a query per attempt and a query per question (which would execute thousands of queries), SQLAlchemy issues exactly 3 batched SQL queries using `IN (...)` clauses.
All topic aggregation, question timing calculations, and strength classifications are then computed in-memory in $O(N)$ linear time.

#### Q8: How is the Cohort Percentile calculated in Story #18? What happens if only 1 student has attempted the topic?
**Answer:**
The cohort percentile represents the percentage of peers in the cohort whose accuracy in that topic is less than or equal to the current student's accuracy:
$$\text{Percentile} = \text{round}\left(100 \times \frac{\sum (\text{peer\_accuracy} \le \text{student\_accuracy})}{\text{total\_cohort\_students}}, 2\right)$$
- If the student is the sole participant in that topic ($N=1$), their percentile is $100.0\%$.
- If the student has completed 0 questions in that topic, the accuracy is $0.0\%$ and the cohort percentile is returned as `None` (empty state handling).

#### Q9: In Story #19 (Learning Progress), how do you compute the Moving Average and Trajectory?
**Answer:**
We order completed attempts chronologically by `completed_at.asc()`.
- **Cumulative Moving Average:** For attempt $k$ with score $s_k$, the moving average is:
  $$\text{MA}_k = \frac{1}{k} \sum_{i=1}^k s_i$$
- **Trajectory:** Evaluates the immediate learning derivative:
  - If $k=1$: `"stable"`
  - If $s_k > s_{k-1}$: `"improving"`
  - If $s_k < s_{k-1}$: `"declining"`
  - If $s_k = s_{k-1}$: `"stable"`
This provides both a smoothed trendline (moving average) and instant feedback on student performance direction.

---

### 3.3 Somesh's Domain: Authentication, WebSockets & Quiz Evaluation

#### Q10: Why did you use JWT for authentication? How are JWT tokens verified?
**Answer:**
JWTs are stateless, compact, and digitally signed tokens.
When a user logs in, the backend signs a payload containing `sub` (user_id), `role`, and `exp` with a secret key using the HMAC-SHA256 (`HS256`) algorithm.
On subsequent requests, the client sends `Authorization: Bearer <token>`.
The server verifies the cryptographic signature without querying the database for every simple endpoint, reducing database load.
For revocation, we verify `token_version` on sensitive endpoints.

#### Q11: How do real-time quiz rooms work over WebSockets (Story #29)?
**Answer:**
FastAPI handles WebSocket connections using an in-memory `ConnectionManager`.
When a student connects to `/ws/quizzes/{room_code}`, the connection is accepted and added to the room's active socket pool.
When a host advances a question or a participant submits an answer, the manager broadcasts JSON events (`QUESTION_CHANGED`, `PARTICIPANT_JOINED`, `QUIZ_COMPLETED`) to all active sockets in that room asynchronously using `asyncio.gather()`.

#### Q12: How are quiz submissions scored and expired (Story #28)?
**Answer:**
When an attempt is completed:
1. The server loads the quiz questions and correct answer keys from the database.
2. It compares the submitted answer map against the correct keys:
   $$\text{Score} = \text{round}\left(\frac{\text{correct\_answers}}{\text{total\_questions}} \times 100\right)$$
3. If the attempt duration exceeds `quiz.duration_minutes`, the status is transitioned to `AttemptStatus.EXPIRED`.
4. Crucially, the correct answers are never sent to the client during active participation; evaluation happens strictly server-side.

---

### 3.4 Soumik's Domain: Quizzes & Participation

#### Q13: How are quiz room codes generated, and how do you avoid collisions?
**Answer:**
Room codes are generated as random 6-character alphanumeric uppercase strings using Python's cryptographically secure `secrets` module:
```python
alphabet = string.ascii_uppercase + string.digits
code = "".join(secrets.choice(alphabet) for _ in range(6))
```
A database query checks if `code` already exists in `quizzes`. If a collision occurs (which has probability $< \frac{1}{36^6}$), the generator retries up to 10 times. A database unique constraint on `quizzes.room_code` guarantees uniqueness.

#### Q14: What is the difference between `/dashboard/performance` (Story #17) and `/analytics/topics` (Story #18)?
**Answer:**
- `/dashboard/performance` (Story #17) is an executive overview for the home dashboard: it provides overall quiz totals, high-level average score, overall time-per-question across all quizzes, and recent attempt logs.
- `/analytics/topics` (Story #18) is a specialized deep-dive diagnostic tool: it calculates per-topic accuracy, per-topic question timing, topic-specific cohort percentiles, and categorizes subjects into strong and weak areas for targeted revision.

---

### 3.5 Shubham's Domain: Study Materials & S3 Storage

#### Q15: Why did you decouple study material storage into S3 instead of storing blobs in PostgreSQL?
**Answer:**
Storing large binary objects (PDFs, images) directly in PostgreSQL (e.g. `BYTEA` columns) degrades database performance:
- It bloats database backups and table pages.
- It consumes database connection memory and causes WAL (Write-Ahead Logging) bloat.
- Decoupling to an S3-compatible object store allows binary files to be streamed directly via HTTP chunking, while PostgreSQL only stores structured metadata (`storage_key`, `course_code`, `file_size`, `mime_type`).

#### Q16: How do you handle atomic uploads and orphaned files if an upload fails halfway?
**Answer:**
In `POST /materials/upload`:
1. The file is uploaded to the S3 bucket under a unique UUID key.
2. The database transaction is executed to insert the `StudyMaterial` record.
3. If the database insertion raises an exception, the `except` block catches it, rolls back the DB transaction, and explicitly invokes `storage.delete_object(Bucket=..., Key=...)` to clean up the newly created S3 object, guaranteeing zero orphaned files.
