import { useState, useEffect, FormEvent } from "react";
import { Question, QuestionCreatePayload } from "../types";
import {
  listQuestions,
  getMyQuestions,
  createQuestion,
  updateQuestion,
  deleteQuestion,
  getQuestionCategories,
} from "../api";

export default function QuestionBank() {
  const [activeTab, setActiveTab] = useState<"browse" | "create" | "my">("browse");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [myQuestions, setMyQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  // Filters
  const [subjectFilter, setSubjectFilter] = useState("");
  const [topicFilter, setTopicFilter] = useState("");
  const [difficultyFilter, setDifficultyFilter] = useState("");
  const [categories, setCategories] = useState<{ subjects: string[]; topics: string[]; difficulties: string[] }>({
    subjects: [],
    topics: [],
    difficulties: [],
  });

  // Create Form State
  const [questionText, setQuestionText] = useState("");
  const [options, setOptions] = useState<string[]>(["", "", "", ""]);
  const [correctAnswerIndex, setCorrectAnswerIndex] = useState<number>(0);
  const [subject, setSubject] = useState("Computer Science");
  const [topic, setTopic] = useState("Database Systems");
  const [difficulty, setDifficulty] = useState("medium");
  const [explanation, setExplanation] = useState("");

  // Edit State
  const [editingQuestion, setEditingQuestion] = useState<Question | null>(null);

  async function loadData() {
    setLoading(true);
    try {
      const [allQ, myQ, cats] = await Promise.all([
        listQuestions({
          subject: subjectFilter || undefined,
          topic: topicFilter || undefined,
          difficulty: difficultyFilter || undefined,
        }),
        getMyQuestions(),
        getQuestionCategories().catch(() => ({ subjects: [], topics: [], difficulties: [] })),
      ]);
      setQuestions(allQ);
      setMyQuestions(myQ);
      setCategories(cats);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load questions";
      setMessage({ text: msg, type: "error" });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, [subjectFilter, topicFilter, difficultyFilter]);

  function handleOptionChange(index: number, val: string) {
    const next = [...options];
    next[index] = val;
    setOptions(next);
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setMessage(null);
    if (options.some((opt) => !opt.trim())) {
      setMessage({ text: "All 4 options must be non-empty", type: "error" });
      return;
    }

    try {
      const payload: QuestionCreatePayload = {
        question_text: questionText.trim(),
        options: options.map((o) => o.trim()),
        correct_answer_index: correctAnswerIndex,
        subject: subject.trim(),
        topic: topic.trim(),
        difficulty,
        explanation: explanation.trim() || undefined,
      };

      if (editingQuestion) {
        await updateQuestion(editingQuestion.id, payload);
        setMessage({ text: "Question updated successfully! (Status reset to PENDING for review)", type: "success" });
        setEditingQuestion(null);
      } else {
        await createQuestion(payload);
        setMessage({ text: "Question created and submitted to moderation queue!", type: "success" });
      }

      // Reset form
      setQuestionText("");
      setOptions(["", "", "", ""]);
      setCorrectAnswerIndex(0);
      setExplanation("");
      setActiveTab("my");
      void loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to submit question";
      setMessage({ text: msg, type: "error" });
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Are you sure you want to delete this question?")) return;
    try {
      await deleteQuestion(id);
      setMessage({ text: "Question deleted successfully", type: "success" });
      void loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete question";
      setMessage({ text: msg, type: "error" });
    }
  }

  function startEdit(q: Question) {
    setEditingQuestion(q);
    setQuestionText(q.question_text);
    setOptions(q.options.length >= 4 ? q.options.slice(0, 4) : [...q.options, "", "", ""].slice(0, 4));
    setSubject(q.subject);
    setTopic(q.topic);
    setDifficulty(q.difficulty);
    setExplanation(q.explanation || "");
    setActiveTab("create");
  }

  return (
    <div className="feature-container">
      <div className="section-header">
        <div>
          <h2>Collaborative Question Bank</h2>
          <p className="subtitle">Contribute, categorize, and practice verified questions</p>
        </div>
        <div className="tab-pill-group">
          <button
            type="button"
            className={activeTab === "browse" ? "pill-btn active" : "pill-btn"}
            onClick={() => { setActiveTab("browse"); setEditingQuestion(null); }}
          >
            Browse ({questions.length})
          </button>
          <button
            type="button"
            className={activeTab === "create" ? "pill-btn active" : "pill-btn"}
            onClick={() => setActiveTab("create")}
          >
            {editingQuestion ? "Edit Question" : "+ Contribute"}
          </button>
          <button
            type="button"
            className={activeTab === "my" ? "pill-btn active" : "pill-btn"}
            onClick={() => { setActiveTab("my"); setEditingQuestion(null); }}
          >
            My Questions ({myQuestions.length})
          </button>
        </div>
      </div>

      {message && (
        <div className={`banner-alert ${message.type === "success" ? "banner-success" : "banner-error"}`}>
          {message.text}
        </div>
      )}

      {/* ================= TAB 1: BROWSE ================= */}
      {activeTab === "browse" && (
        <div>
          <div className="filter-bar">
            <div>
              <label htmlFor="filter-sub">Subject</label>
              <select
                id="filter-sub"
                value={subjectFilter}
                onChange={(e) => setSubjectFilter(e.target.value)}
              >
                <option value="">All Subjects</option>
                {categories.subjects.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="filter-top">Topic</label>
              <select
                id="filter-top"
                value={topicFilter}
                onChange={(e) => setTopicFilter(e.target.value)}
              >
                <option value="">All Topics</option>
                {categories.topics.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="filter-diff">Difficulty</label>
              <select
                id="filter-diff"
                value={difficultyFilter}
                onChange={(e) => setDifficultyFilter(e.target.value)}
              >
                <option value="">All Difficulties</option>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
          </div>

          {loading ? (
            <p className="loading-state">Loading questions…</p>
          ) : questions.length === 0 ? (
            <div className="empty-state">
              <p>No approved questions found matching these filters.</p>
              <button type="button" onClick={() => setActiveTab("create")}>Contribute the first question</button>
            </div>
          ) : (
            <div className="cards-grid">
              {questions.map((q) => (
                <div key={q.id} className="item-card">
                  <div className="card-top">
                    <span className="badge badge-subject">{q.subject}</span>
                    <span className="badge badge-topic">{q.topic}</span>
                    <span className={`badge badge-diff badge-${q.difficulty.toLowerCase()}`}>
                      {q.difficulty}
                    </span>
                  </div>
                  <h3 className="card-prompt">{q.question_text}</h3>
                  <div className="options-display">
                    {q.options.map((opt, idx) => (
                      <div key={idx} className="option-row">
                        <span className="option-letter">{String.fromCharCode(65 + idx)}</span>
                        <span>{opt}</span>
                      </div>
                    ))}
                  </div>
                  {q.explanation && (
                    <div className="explanation-box">
                      <strong>Explanation:</strong> {q.explanation}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ================= TAB 2: CREATE / EDIT ================= */}
      {activeTab === "create" && (
        <form onSubmit={handleCreate} className="styled-form">
          <h3>{editingQuestion ? `Edit Question #${editingQuestion.id}` : "Contribute a Multiple Choice Question"}</h3>
          <p className="form-subtext">All submitted questions are reviewed by moderators before inclusion in public sets.</p>

          <label htmlFor="q-prompt">Question Prompt *</label>
          <textarea
            id="q-prompt"
            rows={3}
            value={questionText}
            onChange={(e) => setQuestionText(e.target.value)}
            placeholder="e.g. Which normal form eliminates partial functional dependency?"
            required
          />

          <label>Answer Options & Correct Key *</label>
          <div className="options-form-group">
            {options.map((opt, idx) => (
              <div key={idx} className="option-input-row">
                <input
                  type="radio"
                  name="correct_choice"
                  id={`choice_${idx}`}
                  checked={correctAnswerIndex === idx}
                  onChange={() => setCorrectAnswerIndex(idx)}
                  title="Mark as correct answer"
                  required
                />
                <span className="option-label-badge">{String.fromCharCode(65 + idx)}</span>
                <input
                  type="text"
                  value={opt}
                  onChange={(e) => handleOptionChange(idx, e.target.value)}
                  placeholder={`Option ${String.fromCharCode(65 + idx)}`}
                  required
                />
                {correctAnswerIndex === idx && <span className="correct-tag">Correct Key</span>}
              </div>
            ))}
          </div>

          <div className="form-row-3">
            <div>
              <label htmlFor="q-sub">Subject *</label>
              <input
                id="q-sub"
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                required
              />
            </div>
            <div>
              <label htmlFor="q-top">Topic *</label>
              <input
                id="q-top"
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                required
              />
            </div>
            <div>
              <label htmlFor="q-diff">Difficulty *</label>
              <select
                id="q-diff"
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
              >
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
          </div>

          <label htmlFor="q-exp">Explanation / Context (Optional)</label>
          <input
            id="q-exp"
            type="text"
            value={explanation}
            onChange={(e) => setExplanation(e.target.value)}
            placeholder="Brief explanation of why this answer is correct"
          />

          <div className="form-actions">
            <button type="submit">{editingQuestion ? "Save Changes" : "Submit Question"}</button>
            {editingQuestion && (
              <button
                type="button"
                className="secondary"
                onClick={() => { setEditingQuestion(null); setActiveTab("my"); }}
              >
                Cancel
              </button>
            )}
          </div>
        </form>
      )}

      {/* ================= TAB 3: MY QUESTIONS ================= */}
      {activeTab === "my" && (
        <div>
          <h3>My Contributed Questions</h3>
          {myQuestions.length === 0 ? (
            <div className="empty-state">
              <p>You haven't contributed any questions yet.</p>
              <button type="button" onClick={() => setActiveTab("create")}>Create your first question</button>
            </div>
          ) : (
            <div className="cards-grid">
              {myQuestions.map((q) => (
                <div key={q.id} className="item-card">
                  <div className="card-top">
                    <span className={`status-badge status-${q.status.toLowerCase()}`}>
                      {q.status}
                    </span>
                    <span className="badge badge-subject">{q.subject}</span>
                    <span className="badge badge-topic">{q.topic}</span>
                  </div>
                  <h4 className="card-prompt">{q.question_text}</h4>
                  <div className="options-display">
                    {q.options.map((opt, idx) => (
                      <div key={idx} className="option-row">
                        <span className="option-letter">{String.fromCharCode(65 + idx)}</span>
                        <span>{opt}</span>
                      </div>
                    ))}
                  </div>
                  {q.moderation_comment && (
                    <div className="moderator-note">
                      <strong>Moderator note:</strong> {q.moderation_comment}
                    </div>
                  )}
                  <div className="card-footer-actions">
                    <button type="button" className="small-btn secondary" onClick={() => startEdit(q)}>
                      Edit
                    </button>
                    <button type="button" className="small-btn danger-btn" onClick={() => handleDelete(q.id)}>
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
