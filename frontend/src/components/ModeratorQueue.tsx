import { useState, useEffect } from "react";
import { Question } from "../types";
import { getModerationQueue, approveQuestion, rejectQuestion } from "../api";

export default function ModeratorQueue() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [filter, setFilter] = useState<string>("pending");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  // Reject State
  const [rejectingId, setRejectingId] = useState<number | null>(null);
  const [rejectComment, setRejectComment] = useState("");

  async function loadQueue() {
    setLoading(true);
    try {
      const data = await getModerationQueue(filter || undefined);
      setQuestions(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load moderation queue";
      setMessage({ text: msg, type: "error" });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadQueue();
  }, [filter]);

  async function handleApprove(id: number) {
    try {
      await approveQuestion(id);
      setMessage({ text: `Question #${id} approved! Included in public bank.`, type: "success" });
      void loadQueue();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to approve question";
      setMessage({ text: msg, type: "error" });
    }
  }

  async function handleReject(id: number) {
    try {
      await rejectQuestion(id, rejectComment.trim() || undefined);
      setMessage({ text: `Question #${id} rejected with feedback.`, type: "success" });
      setRejectingId(null);
      setRejectComment("");
      void loadQueue();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to reject question";
      setMessage({ text: msg, type: "error" });
    }
  }

  return (
    <div className="feature-container">
      <div className="section-header">
        <div>
          <h2>🛡️ Moderator Review Queue</h2>
          <p className="subtitle">Review student contributions to maintain question bank quality</p>
        </div>
        <div className="tab-pill-group">
          <button
            type="button"
            className={filter === "pending" ? "pill-btn active" : "pill-btn"}
            onClick={() => setFilter("pending")}
          >
            Pending Review
          </button>
          <button
            type="button"
            className={filter === "approved" ? "pill-btn active" : "pill-btn"}
            onClick={() => setFilter("approved")}
          >
            Approved
          </button>
          <button
            type="button"
            className={filter === "rejected" ? "pill-btn active" : "pill-btn"}
            onClick={() => setFilter("rejected")}
          >
            Rejected
          </button>
          <button
            type="button"
            className={filter === "" ? "pill-btn active" : "pill-btn"}
            onClick={() => setFilter("")}
          >
            All
          </button>
        </div>
      </div>

      {message && (
        <div className={`banner-alert ${message.type === "success" ? "banner-success" : "banner-error"}`}>
          {message.text}
        </div>
      )}

      {loading ? (
        <p className="loading-state">Loading review queue…</p>
      ) : questions.length === 0 ? (
        <div className="empty-state">
          <p>No questions found in this moderation status ({filter || "ALL"}).</p>
        </div>
      ) : (
        <div className="cards-grid">
          {questions.map((q) => (
            <div key={q.id} className="item-card moderation-card">
              <div className="card-top">
                <span className={`status-badge status-${q.status.toLowerCase()}`}>
                  {q.status}
                </span>
                <span className="badge badge-subject">{q.subject}</span>
                <span className="badge badge-topic">{q.topic}</span>
                <span className="subtext">By Student #{q.creator_id}</span>
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
              {q.explanation && (
                <div className="explanation-box">
                  <strong>Explanation:</strong> {q.explanation}
                </div>
              )}
              {q.moderation_comment && (
                <div className="moderator-note">
                  <strong>Current comment:</strong> {q.moderation_comment}
                </div>
              )}

              {/* Action buttons */}
              {q.status === "pending" && (
                <div className="moderation-actions">
                  <button
                    type="button"
                    className="approve-btn"
                    onClick={() => handleApprove(q.id)}
                  >
                    ✓ Approve Question
                  </button>
                  {rejectingId === q.id ? (
                    <div className="reject-form-inline">
                      <input
                        type="text"
                        placeholder="Feedback on why rejected (optional)"
                        value={rejectComment}
                        onChange={(e) => setRejectComment(e.target.value)}
                      />
                      <button
                        type="button"
                        className="danger-btn"
                        onClick={() => handleReject(q.id)}
                      >
                        Confirm Rejection
                      </button>
                      <button
                        type="button"
                        className="secondary small-btn"
                        onClick={() => setRejectingId(null)}
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="danger-btn"
                      onClick={() => { setRejectingId(q.id); setRejectComment(""); }}
                    >
                      ✕ Reject
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
