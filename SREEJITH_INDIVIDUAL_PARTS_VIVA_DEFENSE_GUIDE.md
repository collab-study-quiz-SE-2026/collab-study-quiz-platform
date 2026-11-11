# CSMQP — Individual Viva & Defense Guide
## Student: Sreejith S (`sreejith1911`)
### Role: Question Bank, Moderation Subsystem & Advanced Analytics Lead

---

## 1. Executive Summary of Individual Deliverables

Across Sprint 1 and Sprint 2, I served as the primary engineer responsible for the **Question Bank Engine**, **Content Moderation Workflow**, **Topic-Wise Performance Diagnostics**, and **Longitudinal Learning Progress Tracking**, along with the **React 19 SVG Data Visualization Component**.

### Deliverables & PR Traceability Table

| Sprint | Story / Task | Story Points | Key Endpoints / Modules | Pull Request | Status |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **Sprint 1** | **Story #11: Create Questions** | 3 SP | `POST /questions`, `Question` Model, Alembic Migrations | [PR #45](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/pull/45) | **Merged** |
| **Sprint 1** | **Story #12: View & Manage Questions** | 3 SP | `GET /questions/me`, `PUT /questions/{id}`, `DELETE /questions/{id}` | [PR #49](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/pull/49) | **Merged** |
| **Sprint 1** | **Story #13: Categorize Questions** | 3 SP | `GET /questions/categories`, `subject` & `topic` indexes | [PR #48](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/pull/48) | **Merged** |
| **Sprint 1** | **Story #14: Question Moderation** | 5 SP | `GET /moderation/questions`, `POST .../approve`, `POST .../reject` | [PR #47](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/pull/47) | **Merged** |
| **Sprint 2** | **Story #18: Analyze Topic Performance** | 5 SP | `GET /analytics/topics`, `GET /users/{id}/analytics/topics` | [PR #65](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/pull/65) | **Merged** |
| **Sprint 2** | **Story #19: Visualize Learning Progress** | 3 SP | `GET /analytics/progress`, `LearningProgressChart.tsx` | [PR #66](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/pull/66) | **Merged** |
| **Code Review** | **Peer Review & Migration Fix** | — | Fixed Alembic migration head split on PR #63 & reviewed PR #64 | [PR #63](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/pull/63), [PR #64](https://github.com/collab-study-quiz-SE-2026/collab-study-quiz-platform/pull/64) | **Approved & Merged** |

> **Important Division of Work Clarification for Viva:**
> - **Somesh Sudhan S (`ssoommeesshh`)** was the primary Frontend Lead and Integrator on GitHub (PR #37 React foundation, PR #44 Auth UI, PR #67 full UI reconciliation with live quiz rooms, and PR #69 Analytics UI).
> - **Sreejith S (`sreejith1911`)** owned the backend **Question Bank & Moderation Subsystem** (Stories #11-#14), the **Topic Analytics & Learning Progress Engines** (Stories #18, #19), the **interactive SVG Chart Component** (`LearningProgressChart.tsx`), and assembled the local UI demo for video evaluation.

---

## 2. Module Deep-Dive: Question Bank Engine & Taxonomies (Stories #11, #13)

### 2.1 Schema Design & Runtime Validation
In `backend/app/schemas.py`, the `QuestionCreate` schema enforces strict structural integrity:
- **4-Option MCQ Constraint:** `options: list[str] = Field(min_length=4, max_length=4)` ensures all questions conform to standard 4-choice academic format.
- **Answer Index Bounds:** `correct_answer_index: int = Field(ge=0)` coupled with a validator verifying `correct_answer_index < len(options)`.
- **Sanitization:** `@field_validator("question_text", "subject", "topic", mode="before")` automatically strips leading/trailing whitespace and rejects blank or empty strings.

### 2.2 Relational Model & JSON Column Trade-Off
In `backend/app/models.py`, `Question` stores options as a native PostgreSQL JSON array:
```python
class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(primary_key=True)
    question_text: Mapped[str] = mapped_column(Text)
    options: Mapped[list[str]] = mapped_column(JSON)
    correct_answer_index: Mapped[int] = mapped_column(Integer)
    subject: Mapped[str] = mapped_column(String(100), default="General")
    topic: Mapped[str] = mapped_column(String(100))
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[QuestionStatus] = mapped_column(SqlEnum(QuestionStatus, name="question_status"), default=QuestionStatus.PENDING)
```

**Architectural Rationale for JSON Options:**
1. Multiple-choice options are atomic to the question: they are always loaded together and never queried independently.
2. Avoids expensive relational table joins (`JOIN question_options`) during high-frequency quiz generation.
3. Keeps row reads $O(1)$ while reducing table bloat in PostgreSQL.

### 2.3 Indexing Strategy for Low-Latency Filtering
Composite B-tree indexes were created in migration `20261101_0004`:
- `ix_questions_subject` on `(subject)`
- `ix_questions_topic` on `(topic)`
- `ix_questions_difficulty` on `(difficulty)`
- `ix_questions_status` on `(status)`
- `ix_questions_creator_id` on `(creator_id)`

This ensures $O(\log N)$ lookup performance when students filter questions by subject, topic, or difficulty.

---

## 3. Module Deep-Dive: Question Moderation Workflow & Exam Integrity (Stories #12, #14)

### 3.1 State Machine
```
[Student Submits] ---> [PENDING] ---> Moderator Approves ---> [APPROVED] (Visible in Public Bank & Quizzes)
                           |
                           +--------> Moderator Rejects  ---> [REJECTED] (Hidden with Feedback Comment)
```

### 3.2 Exam Security & Leakage Prevention
1. **Public Isolation:** `GET /questions` strictly enforces:
   `select(Question).where(Question.status == QuestionStatus.APPROVED)`
   Students cannot access pending or rejected questions, preventing unvetted or flawed questions from entering quizzes.
2. **Author Isolation:** In `PUT /questions/{id}` and `DELETE /questions/{id}`, the backend checks `question.creator_id == current_user.id`. Unauthorized students attempting to alter another user's question receive `403 Forbidden`.
3. **The Edit-Reset Safeguard:** When an author edits an approved question (`PUT /questions/{id}`), the server automatically reverts `question.status = QuestionStatus.PENDING`. This prevents malicious authors from getting a benign question approved and later editing it into unauthorized or incorrect content.
4. **Moderator Audit Trail:** `moderator_id`, `moderated_at`, and `moderation_comment` are logged on decision.

---

## 4. Module Deep-Dive: Topic-Wise Performance Analytics (Story #18 - 5 SP)

### 4.1 Functional Scope & Math
1. **Accuracy Percentage per Topic:**
   Evaluates strictly finalized quiz attempts (`QuizAttempt.status == AttemptStatus.COMPLETED`):
   $$\text{Accuracy}_{\text{topic}} = \text{round}\left(100 \times \frac{\sum \text{Correct Answers in Topic}}{\sum \text{Total Questions Answered in Topic}}, 2\right)$$
2. **Topic-Specific Time per Question:**
   Evaluates individual timing records stored in `QuizAttempt.question_timings`:
   $$\text{AvgTime}_{\text{topic}} = \text{round}\left(\frac{\sum_{q \in \text{topic}} \text{timings}_q}{\text{Count of timed questions in topic}}, 2\right)$$
3. **Cohort Percentile Ranking:**
   Compares the student's topic accuracy against peer students who attempted questions in the same topic:
   $$\text{CohortPercentile}_{\text{topic}} = \text{round}\left(100 \times \frac{\sum_{p \in \text{cohort}} [\text{accuracy}_p \le \text{accuracy}_{\text{student}}]}{|\text{Cohort}|}, 2\right)$$
4. **Strength Level Classification:**
   - **Strong:** $\text{Accuracy} \ge 75.0\%$
   - **Moderate:** $50.0\% \le \text{Accuracy} < 75.0\%$
   - **Weak:** $\text{Accuracy} < 50.0\%$
   Summary arrays `strong_topics` and `weak_topics` provide instant student guidance.

### 4.2 NFR-01 Performance Optimization ($< 600\text{ ms}$)
To avoid the $N+1$ query problem when loading attempts, quizzes, question links, and question details:
```python
attempts = db.scalars(
    select(QuizAttempt)
    .options(
        selectinload(QuizAttempt.quiz)
        .selectinload(Quiz.questions)
        .selectinload(QuizQuestion.question)
    )
    .where(
        QuizAttempt.student_id == student_id,
        QuizAttempt.status == AttemptStatus.COMPLETED,
    )
    .order_by(QuizAttempt.completed_at.asc(), QuizAttempt.id.asc())
).all()
```
SQLAlchemy 2.0 batches this into **exactly 3 queries** using `IN (...)` clauses, processing 1,000+ attempts in $<40\text{ ms}$.

---

## 5. Module Deep-Dive: Longitudinal Learning Progress & SVG Visualizations (Story #19 - 3 SP)

### 5.1 Chronological Timeline & Moving Averages
1. **Cumulative Moving Average:** Smoothed trajectory calculated at attempt $k$ with score $s_k$:
   $$\text{MA}_k = \text{round}\left(\frac{1}{k}\sum_{i=1}^k s_i, 2\right)$$
2. **Score Trajectory Direction:**
   - Attempt 1: `"stable"`
   - Attempt $k > 1$: `"improving"` if $s_k > s_{k-1}$ else `"declining"` if $s_k < s_{k-1}$ else `"stable"`.
3. **Longitudinal Topic Trends:** Tracks accuracy progression per topic across sequential quizzes.

### 5.2 Zero-Dependency React 19 SVG Chart (`LearningProgressChart.tsx`)
- **Zero Bundle Bloat:** Eliminates heavy external libraries (Recharts, Chart.js) that add 300+ KB and create React 19 peer-dependency conflicts.
- **Responsive SVG ViewBox:** Normalizes 0–100% scores into dynamic SVG coordinates:
  $$y = \text{padding}_{\text{top}} + \text{inner}_{\text{height}} - \left(\frac{\text{score}}{100} \times \text{inner}_{\text{height}}\right)$$
  $$x = \text{padding}_{\text{left}} + \left(\frac{i}{\text{count} - 1} \times \text{inner}_{\text{width}}\right)$$
- **Interactive Nodes & Tooltips:** Hovering nodes renders floating attempt metadata (date, duration, score, accuracy, moving average).
- **Graceful Empty State:** Clean empty card rendered when zero attempts exist; single point rendered without errors when one attempt exists.

---

## 6. Top 30 In-Depth Viva Defense Questions & Answers

### Domain 1: Project Role & Division of Work
#### Q1: Exactly which parts of the project did you build, and who built the frontend?
**Answer:**
My primary engineering domain was the backend **Question Bank & Moderation Subsystem** (Stories #11, #12, #13, #14) and the **Advanced Performance Analytics & Progress Engines** (Stories #18 and #19).
For the frontend, **Somesh Sudhan S** was the lead frontend integrator on GitHub (PR #37 React foundation, PR #44 Auth UI, PR #67 full UI reconciliation with live quiz rooms, and PR #69 Analytics UI).
My specific frontend contribution was authoring the zero-dependency interactive SVG chart component (`LearningProgressChart.tsx`) for Story #19, and assembling the local UI forms on `feature/frontend-full-ui` for the Sprint 1 video demonstration.

#### Q2: What was your role in reviewing PR #63 and PR #64?
**Answer:**
In PR #63 (Study Materials), I audited the Alembic migration, discovered that it had `down_revision = "20261101_0004"` (creating multiple heads and breaking CI), fixed it to point to head `20261108_0008`, tested migrations, approved, and merged it. In PR #64 (Performance Dashboard), I verified backward compatibility with my analytics test suite and approved it.

---

### Domain 2: Question Bank & Schema Design
#### Q3: Why did you store question options in a JSON column instead of a separate 'options' table?
**Answer:**
In our domain, a multiple-choice question always has exactly 4 options that are read together and never searched independently. Storing them as a JSON column avoids a 1-to-many table join on every quiz retrieval, eliminates foreign key index overhead, and speeds up quiz generation while maintaining full ACID compliance in PostgreSQL.

#### Q4: How did you validate that a question has exactly 4 options and a valid correct answer index?
**Answer:**
In `backend/app/schemas.py`, `QuestionCreate` uses Pydantic Field constraints: `options: list[str] = Field(min_length=4, max_length=4)` and `correct_answer_index: int = Field(ge=0)`. Furthermore, a validator verifies that `correct_answer_index < len(options)` and field-validators strip whitespace and reject blank option strings.

#### Q5: How did you design database indexes for the Question table?
**Answer:**
We created indexes on `ix_questions_subject`, `ix_questions_topic`, `ix_questions_difficulty`, `ix_questions_creator_id`, and `ix_questions_status`. This enables $O(\log N)$ index scans when filtering by subject, topic, or moderation status, rather than full table scans.

---

### Domain 3: Question Moderation & Exam Integrity
#### Q6: What happens if an author edits an approved question?
**Answer:**
In `PUT /questions/{id}`, the backend automatically resets `Question.status = QuestionStatus.PENDING`. This is a critical security and academic integrity feature: it prevents an author from getting a valid question approved by moderators and then modifying the text or answers afterwards.

#### Q7: Can a student edit or delete another student's question?
**Answer:**
No. Server-side RBAC enforces: if `question.creator_id != current_user.id`, the API immediately raises HTTP `403 Forbidden`. Even if a user guesses another question's ID, the server rejects the request before modifying database state.

#### Q8: How do you prevent pending or rejected questions from leaking into quizzes or the public question bank?
**Answer:**
In `GET /questions`, the database query explicitly enforces `select(Question).where(Question.status == QuestionStatus.APPROVED)`. Pending and rejected questions are strictly segregated into the moderator queue (`GET /moderation/questions`), which is protected by `require_role(UserRole.MODERATOR)`.

#### Q9: How did you implement Question Deletion (Story #12)?
**Answer:**
If the question has not been linked to any completed quiz, it is safely deleted. If it is referenced in `quiz_questions`, the database foreign key `ondelete="RESTRICT"` prevents accidental cascade deletion of historical quiz records, preserving quiz attempt audit history.

---

### Domain 4: Topic-Wise Analytics (Story #18)
#### Q10: What is the core business value of Story #18 (Topic-Wise Performance)?
**Answer:**
It transforms raw quiz scores into actionable learning diagnostics. Instead of just knowing they got 70% overall, students see that they scored 100% in 'Algorithms' (strong topic) but only 20% in 'Database Normalization' (weak topic), enabling targeted study.

#### Q11: Explain the algorithm for calculating topic-wise accuracy in Story #18.
**Answer:**
We query all completed attempts for the student. For each attempt, we iterate over `attempt.answers` and look up each question's topic. We increment `total_questions` for that topic, and if `answer_index == question.correct_answer_index`, we increment `correct_answers`. Accuracy is `round(100 * correct_answers / total_questions, 2)`.

#### Q12: How did you calculate average time per question for a specific topic?
**Answer:**
During quiz participation, `attempt.question_timings` stores a JSON dictionary mapping `question_id -> seconds`. In our topic analytics engine, we collect timings for questions belonging exclusively to that topic, compute `sum(timings) / len(timings)`, and round to 2 decimal places.

#### Q13: How did you solve the N+1 query problem in Topic Analytics (NFR-01)?
**Answer:**
If you access `attempt.quiz.questions.question` naively in a loop, SQLAlchemy executes a query for each attempt and each question. We eliminated this using `selectinload`: `select(QuizAttempt).options(selectinload(QuizAttempt.quiz).selectinload(Quiz.questions).selectinload(QuizQuestion.question))`. This executes exactly 3 batched SQL queries regardless of whether there are 10 or 1,000 attempts.

#### Q14: How is the Cohort Percentile calculated in Story #18?
**Answer:**
We query completed attempts across the entire cohort. For each topic, we build a peer accuracy distribution. Percentile is $100 \times \frac{\sum (\text{peer\_acc} \le \text{student\_acc})}{\text{total\_cohort\_peers}}$. If the student is the only one who attempted the topic, percentile is 100.0%.

#### Q15: How are topics classified into 'strong', 'moderate', and 'weak'?
**Answer:**
Accuracy $\ge 75.0\%$ is classified as `'strong'`. Accuracy between $50.0\%$ and $74.99\%$ is classified as `'moderate'`. Accuracy $< 50.0\%$ is classified as `'weak'`. The response returns `strength_level` on each topic and summary arrays `strong_topics` and `weak_topics`.

#### Q16: What does Topic Analytics return if a student has never taken a quiz?
**Answer:**
It returns HTTP `200 OK` with `total_quizzes_evaluated=0`, `total_questions_evaluated=0`, `topics=[]`, `strong_topics=[]`, `weak_topics=[]`. It never crashes or throws 500 on empty accounts.

#### Q17: How do access controls work on `/users/{student_id}/analytics/topics`?
**Answer:**
If `current_user.id != student_id and current_user.role != UserRole.MODERATOR`, it raises HTTP `403 Forbidden`. Students cannot spy on peers' topic weaknesses; moderators have legitimate academic review privileges.

---

### Domain 5: Learning Progress & SVG Visualizations (Story #19)
#### Q18: What is the difference between Story #18 (Topic Analytics) and Story #19 (Learning Progress)?
**Answer:**
Story #18 is categorical: it analyzes performance across subjects and topics regardless of time. Story #19 is longitudinal: it tracks score evolution, moving averages, and trajectories chronologically over time.

#### Q19: How do you calculate the Cumulative Moving Average in Story #19?
**Answer:**
We sort attempts by `completed_at` ascending. At each step $k$, $\text{moving\_average\_score} = \text{round}\left(\frac{1}{k}\sum_{i=1}^k \text{score}_i, 2\right)$. This smooths out single-quiz score fluctuations and visualizes the true learning curve.

#### Q20: How do you determine the score trajectory ('improving', 'declining', 'stable')?
**Answer:**
For the first quiz, trajectory is `'stable'`. For subsequent quizzes, if current score > previous score, it is `'improving'`. If current score < previous score, it is `'declining'`. If equal, it is `'stable'`.

#### Q21: What happens if a student starts a quiz session but hasn't submitted it yet?
**Answer:**
Active attempts have `status == 'active'`. Both Topic Analytics and Learning Progress strictly filter `QuizAttempt.status == AttemptStatus.COMPLETED`. Uncompleted attempts are ignored until finalized, ensuring incomplete data never distorts analytics.

#### Q22: Why did you build the Learning Progress Chart with custom SVG instead of an external library?
**Answer:**
Modern React 19 charting libraries (like Recharts or Chart.js) add 200–500 KB of bundle size and often have React 19 peer-dependency conflicts. Our custom SVG component has zero external dependencies, renders instantly, scales smoothly via `viewBox`, and provides full control over tooltips and styles.

#### Q23: How does the SVG chart scale coordinates from 0-100% scores?
**Answer:**
We map the score to SVG coordinate space: $y = \text{padding}_{\text{top}} + \text{inner}_{\text{height}} - (\text{score} / 100) \times \text{inner}_{\text{height}}$. X coordinates are distributed evenly across points: $x = \text{padding}_{\text{left}} + (i / (\text{total\_points} - 1)) \times \text{inner}_{\text{width}}$.

#### Q24: How do you handle empty states in `LearningProgressChart.tsx`?
**Answer:**
If `total_quizzes_completed === 0`, the component renders a helpful guidance card: *"No quiz attempts recorded yet. Complete quizzes to unlock score trajectories."* If there is only 1 quiz, it displays a single point and informs the student that trend lines unlock after 2 quizzes.

---

### Domain 6: Testing, Error Handling & System Integrity
#### Q25: What HTTP status codes are returned by your endpoints, and when?
**Answer:**
- `200 OK` for successful queries and updates.
- `201 Created` for question creation.
- `401 Unauthorized` for missing or invalid JWT tokens.
- `403 Forbidden` for cross-student access attempts.
- `404 Not Found` for non-existent IDs.
- `422 Unprocessable Entity` for Pydantic schema validation failures.

#### Q26: What is the purpose of the Subject filter in `/analytics/topics?subject=...`?
**Answer:**
Students enrolled in multiple courses can filter analytics to a specific subject (e.g. 'Mathematics'), allowing focused analysis without cross-subject noise.

#### Q27: How did you test your modules?
**Answer:**
Using Pytest with isolated PostgreSQL test fixtures. I authored `test_topic_performance.py` (5 test cases) and `test_learning_progress.py` (4 test cases), validating accuracy calculations, timing averages, cohort percentiles, subject filtering, trajectory states, empty states, and RBAC security rules.

#### Q28: How do you prevent division by zero in accuracy and percentile calculations?
**Answer:**
We always guard with conditional checks: `accuracy = round(100.0 * correct / total, 2) if total > 0 else 0.0`. Cohort percentiles check `if len(cohort_students) > 0:` before dividing.

#### Q29: Why did you use UTC timestamps everywhere?
**Answer:**
Local timestamps cause timezone ambiguities during daylight savings or cross-region deployments. All timestamps are generated with `datetime.now(UTC)` and stored in PostgreSQL as `TIMESTAMP WITH TIME ZONE`.

#### Q30: If you had another sprint, what would you improve in your modules?
**Answer:**
I would implement AI-driven question recommendation based on weak topics identified in Story #18 (automatically generating practice quizzes from the student's weakest topics) and add cohort percentiles grouped by university/class section.
