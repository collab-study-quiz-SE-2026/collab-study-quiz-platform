import { useState, useEffect, FormEvent } from "react";
import { Quiz, QuizAttempt, Question } from "../types";
import LiveQuizRoom from "./LiveQuizRoom";
import {
  listQuizzes,
  getQuiz,
  createQuiz,
  joinQuizByRoom,
  startQuizSession,
  submitQuizAnswer,
  completeQuizSession,
  listQuestions,
} from "../api";

export default function Quizzes() {
  const [activeTab, setActiveTab] = useState<"play" | "create">("play");
  const [quizzes, setQuizzes] = useState<Quiz[]>([]);
  const [approvedQuestions, setApprovedQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  // Join Room State
  const [roomCodeInput, setRoomCodeInput] = useState("");

  // Create Quiz State
  const [quizTitle, setQuizTitle] = useState("");
  const [quizDesc, setQuizDesc] = useState("");
  const [durationMinutes, setDurationMinutes] = useState(15);
  const [maxAttempts, setMaxAttempts] = useState(1);
  const [selectedQuestionIds, setSelectedQuestionIds] = useState<number[]>([]);
  const [createdQuiz, setCreatedQuiz] = useState<Quiz | null>(null);

  // Active Quiz Play State
  const [activeQuiz, setActiveQuiz] = useState<Quiz | null>(null);
  const [activeAttempt, setActiveAttempt] = useState<QuizAttempt | null>(null);
  const [liveRoom, setLiveRoom] = useState<{ roomCode: string } | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswerIndex, setSelectedAnswerIndex] = useState<number | null>(null);
  const [questionStartTime, setQuestionStartTime] = useState<number>(Date.now());
  const [quizResult, setQuizResult] = useState<QuizAttempt | null>(null);

  async function loadInitialData() {
    setLoading(true);
    try {
      const [qzList, qList] = await Promise.all([
        listQuizzes().catch(() => []),
        listQuestions().catch(() => []),
      ]);
      setQuizzes(qzList);
      setApprovedQuestions(qList);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadInitialData();
  }, []);

  async function handleJoinRoom(code: string) {
    if (!code.trim()) return;
    setMessage(null);
    try {
      await joinQuizByRoom(code.trim());
      setLiveRoom({ roomCode: code.trim().toUpperCase() });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to join quiz room";
      setMessage({ text: msg, type: "error" });
    }
  }

  async function handleStartQuiz(quizId: number) {
    setMessage(null);
    try {
      const attempt = await startQuizSession(quizId);
      const quizData = await getQuiz(quizId);
      setActiveAttempt(attempt);
      setActiveQuiz(quizData);
      setCurrentQuestionIndex(0);
      setSelectedAnswerIndex(null);
      setQuestionStartTime(Date.now());
      setQuizResult(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to start quiz";
      setMessage({ text: msg, type: "error" });
    }
  }

  async function handleAnswerSubmit() {
    if (!activeAttempt || !activeQuiz) return;
    const currentQ = activeQuiz.questions[currentQuestionIndex];
    if (selectedAnswerIndex === null) {
      alert("Please select an answer choice");
      return;
    }

    const timeSpent = Math.max(1, Math.round((Date.now() - questionStartTime) / 1000));
    try {
      const updatedAttempt = await submitQuizAnswer(
        activeAttempt.id,
        currentQ.id,
        selectedAnswerIndex,
        timeSpent
      );
      setActiveAttempt(updatedAttempt);

      // Move to next question or complete
      if (currentQuestionIndex + 1 < activeQuiz.questions.length) {
        setCurrentQuestionIndex(currentQuestionIndex + 1);
        setSelectedAnswerIndex(null);
        setQuestionStartTime(Date.now());
      } else {
        await handleFinishQuiz(activeAttempt.id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to submit answer";
      setMessage({ text: msg, type: "error" });
    }
  }

  async function handleFinishQuiz(attemptId: number) {
    try {
      const result = await completeQuizSession(attemptId);
      setQuizResult(result);
      setActiveQuiz(null);
      setActiveAttempt(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to finalize quiz";
      setMessage({ text: msg, type: "error" });
    }
  }

  async function handleCreateQuiz(e: FormEvent) {
    e.preventDefault();
    setMessage(null);
    if (selectedQuestionIds.length === 0) {
      setMessage({ text: "Please select at least 1 question for the quiz", type: "error" });
      return;
    }

    try {
      const created = await createQuiz({
        title: quizTitle.trim(),
        description: quizDesc.trim(),
        duration_minutes: durationMinutes,
        max_attempts: maxAttempts,
        question_ids: selectedQuestionIds,
      });
      setCreatedQuiz(created);
      setMessage({ text: `Quiz created! Room Code: ${created.room_code}`, type: "success" });
      setQuizTitle("");
      setQuizDesc("");
      setSelectedQuestionIds([]);
      void loadInitialData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create quiz";
      setMessage({ text: msg, type: "error" });
    }
  }

  function toggleQuestionSelection(qId: number) {
    if (selectedQuestionIds.includes(qId)) {
      setSelectedQuestionIds(selectedQuestionIds.filter((id) => id !== qId));
    } else {
      setSelectedQuestionIds([...selectedQuestionIds, qId]);
    }
  }

  if (liveRoom) {
    return (
      <LiveQuizRoom
        roomCode={liveRoom.roomCode}
        onLeave={() => {
          setLiveRoom(null);
          setQuizResult(null);
          void loadInitialData();
        }}
      />
    );
  }

  return (
    <div className="feature-container">
      <div className="section-header">
        <div>
          <h2>Quizzes & Live Multiplayer Rooms</h2>
          <p className="subtitle">Compete in synchronized quiz rooms or take practice quizzes</p>
        </div>
        <div className="tab-pill-group">
          <button
            type="button"
            className={activeTab === "play" && !activeQuiz ? "pill-btn active" : "pill-btn"}
            onClick={() => { setActiveTab("play"); setActiveQuiz(null); setQuizResult(null); }}
          >
            Play Quiz
          </button>
          <button
            type="button"
            className={activeTab === "create" ? "pill-btn active" : "pill-btn"}
            onClick={() => { setActiveTab("create"); setActiveQuiz(null); setQuizResult(null); }}
          >
            + Host / Create Quiz
          </button>
        </div>
      </div>

      {message && (
        <div className={`banner-alert ${message.type === "success" ? "banner-success" : "banner-error"}`}>
          {message.text}
        </div>
      )}

      {/* ================= ACTIVE QUIZ PLAYER ================= */}
      {activeQuiz && activeAttempt && (
        <div className="quiz-player-card">
          <div className="quiz-player-header">
            <div>
              <h3>{activeQuiz.title}</h3>
              <p className="subtext">
                Question {currentQuestionIndex + 1} of {activeQuiz.questions.length}
              </p>
            </div>
            <div className="quiz-timer-badge">
              ⏱️ {activeQuiz.duration_minutes}m time limit
            </div>
          </div>

          {activeQuiz.questions[currentQuestionIndex] && (
            <div className="quiz-question-body">
              <h4 className="player-prompt">
                {activeQuiz.questions[currentQuestionIndex].question_text}
              </h4>
              <div className="player-options-list">
                {activeQuiz.questions[currentQuestionIndex].options.map((opt, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className={`quiz-choice-btn ${selectedAnswerIndex === idx ? "selected" : ""}`}
                    onClick={() => setSelectedAnswerIndex(idx)}
                  >
                    <span className="choice-badge">{String.fromCharCode(65 + idx)}</span>
                    <span className="choice-text">{opt}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="quiz-player-footer">
            <button
              type="button"
              className="secondary"
              onClick={() => handleFinishQuiz(activeAttempt.id)}
            >
              Submit & End Early
            </button>
            <button type="button" onClick={handleAnswerSubmit}>
              {currentQuestionIndex + 1 === activeQuiz.questions.length
                ? "Finish & Grade Quiz"
                : "Submit Answer & Next →"}
            </button>
          </div>
        </div>
      )}

      {/* ================= QUIZ RESULT BANNER ================= */}
      {quizResult && (
        <div className="result-card">
          <div className="result-icon">🎉</div>
          <h3>Quiz Completed!</h3>
          <div className="score-display">
            Score: <span className="score-number">{quizResult.score !== null ? `${quizResult.score}%` : "Recorded"}</span>
          </div>
          <p>Your score and attempt timing have been saved to your account attempt history.</p>
          <button
            type="button"
            onClick={() => { setQuizResult(null); setActiveTab("play"); }}
          >
            Back to Available Quizzes
          </button>
        </div>
      )}

      {/* ================= TAB 1: PLAY QUIZZES ================= */}
      {!activeQuiz && !quizResult && activeTab === "play" && (
        <div>
          {/* Join by Room Code Box */}
          <div className="join-room-box">
            <h3>Enter 6-Character Room Code</h3>
            <p>Join a live room configured by your instructor or peer</p>
            <div className="room-input-row">
              <input
                type="text"
                placeholder="e.g. ABC123"
                maxLength={6}
                value={roomCodeInput}
                onChange={(e) => setRoomCodeInput(e.target.value.toUpperCase())}
                className="room-code-field"
              />
              <button
                type="button"
                onClick={() => handleJoinRoom(roomCodeInput)}
                disabled={roomCodeInput.trim().length !== 6}
              >
                Join Room
              </button>
            </div>
          </div>

          <h3 className="section-title">Available Practice Quizzes</h3>
          {loading ? (
            <p className="loading-state">Loading quizzes…</p>
          ) : quizzes.length === 0 ? (
            <div className="empty-state">
              <p>No published quizzes yet. Create the first quiz!</p>
              <button type="button" onClick={() => setActiveTab("create")}>Create Quiz</button>
            </div>
          ) : (
            <div className="cards-grid">
              {quizzes.map((qz) => (
                <div key={qz.id} className="item-card quiz-card">
                  <div className="card-top">
                    <span className="room-code-tag">Room: {qz.room_code}</span>
                    <span className="badge badge-diff">{qz.duration_minutes} mins</span>
                  </div>
                  <h4>{qz.title}</h4>
                  <p className="desc-text">{qz.description || "Self-paced practice quiz."}</p>
                  <p className="subtext">
                    {qz.questions.length} Questions • Max Attempts: {qz.max_attempts}
                  </p>
                  <button
                    type="button"
                    className="full-btn"
                    onClick={() => handleStartQuiz(qz.id)}
                  >
                    Start Quiz Now
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ================= TAB 2: CREATE QUIZ ================= */}
      {!activeQuiz && !quizResult && activeTab === "create" && (
        <div>
          {createdQuiz && (
            <div className="created-quiz-banner">
              <h4>🎯 Quiz Created Successfully!</h4>
              <p>Share this 6-character room code with other students:</p>
              <div className="code-box">{createdQuiz.room_code}</div>
              <p className="subtext">Students can join using this code on the Play tab.</p>
              <button
                type="button"
                onClick={() => setLiveRoom({ roomCode: createdQuiz.room_code })}
              >
                Open live room as host
              </button>
            </div>
          )}

          <form onSubmit={handleCreateQuiz} className="styled-form">
            <h3>Configure New Quiz</h3>
            <p className="form-subtext">Assemble approved questions from the shared Question Bank.</p>

            <label htmlFor="qz-title">Quiz Title *</label>
            <input
              id="qz-title"
              type="text"
              value={quizTitle}
              onChange={(e) => setQuizTitle(e.target.value)}
              placeholder="e.g. Database Normalization & Indexing Challenge"
              required
            />

            <label htmlFor="qz-desc">Description</label>
            <textarea
              id="qz-desc"
              rows={2}
              value={quizDesc}
              onChange={(e) => setQuizDesc(e.target.value)}
              placeholder="Instructions or topic summary"
            />

            <div className="form-row-2">
              <div>
                <label htmlFor="qz-dur">Duration (Minutes) *</label>
                <input
                  id="qz-dur"
                  type="number"
                  min={1}
                  max={180}
                  value={durationMinutes}
                  onChange={(e) => setDurationMinutes(parseInt(e.target.value) || 15)}
                  required
                />
              </div>
              <div>
                <label htmlFor="qz-att">Max Attempts (1–10) *</label>
                <input
                  id="qz-att"
                  type="number"
                  min={1}
                  max={10}
                  value={maxAttempts}
                  onChange={(e) => setMaxAttempts(parseInt(e.target.value) || 1)}
                  required
                />
              </div>
            </div>

            <label>Select Approved Questions ({selectedQuestionIds.length} selected) *</label>
            {approvedQuestions.length === 0 ? (
              <p className="empty-subtext">No approved questions available yet. Submit and approve questions first!</p>
            ) : (
              <div className="question-picker-list">
                {approvedQuestions.map((q) => (
                  <label key={q.id} className="question-picker-item">
                    <input
                      type="checkbox"
                      checked={selectedQuestionIds.includes(q.id)}
                      onChange={() => toggleQuestionSelection(q.id)}
                    />
                    <div className="picker-text">
                      <strong>#{q.id} {q.question_text}</strong>
                      <span className="picker-meta">
                        {q.subject} • {q.topic} • {q.difficulty}
                      </span>
                    </div>
                  </label>
                ))}
              </div>
            )}

            <button type="submit" disabled={selectedQuestionIds.length === 0}>
              Create Quiz & Generate Room Code
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
