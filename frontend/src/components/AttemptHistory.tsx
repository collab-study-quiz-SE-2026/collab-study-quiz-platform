import { useState, useEffect } from "react";
import { QuizAttemptHistory } from "../types";
import { getMyAttemptHistory } from "../api";

export default function AttemptHistory() {
  const [history, setHistory] = useState<QuizAttemptHistory[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadHistory() {
    setLoading(true);
    try {
      const data = await getMyAttemptHistory();
      setHistory(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load attempt history";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadHistory();
  }, []);

  function formatDuration(seconds?: number | null): string {
    if (!seconds) return "—";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins === 0) return `${secs}s`;
    return `${mins}m ${secs}s`;
  }

  function formatDate(isoString: string): string {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return isoString;
    }
  }

  return (
    <div className="feature-container">
      <div className="section-header">
        <div>
          <h2>My Quiz Attempt History</h2>
          <p className="subtitle">Track your past scores, completion times, and learning performance</p>
        </div>
        <button type="button" className="secondary" onClick={() => void loadHistory()}>
          ↻ Refresh
        </button>
      </div>

      {error && <div className="banner-alert banner-error">{error}</div>}

      {loading ? (
        <p className="loading-state">Loading attempt history…</p>
      ) : history.length === 0 ? (
        <div className="empty-state">
          <p>No completed quiz attempts yet. Join a quiz to see your scores here!</p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="styled-table">
            <thead>
              <tr>
                <th>Attempt #</th>
                <th>Quiz Title</th>
                <th>Status</th>
                <th>Score</th>
                <th>Time Spent</th>
                <th>Date Completed</th>
              </tr>
            </thead>
            <tbody>
              {history.map((att) => (
                <tr key={att.id}>
                  <td><strong>#{att.id}</strong></td>
                  <td>{att.quiz_title}</td>
                  <td>
                    <span className={`status-badge status-${att.status.toLowerCase()}`}>
                      {att.status}
                    </span>
                  </td>
                  <td>
                    <span className="score-badge">
                      {att.score !== null ? `${att.score}%` : "—"}
                    </span>
                  </td>
                  <td>{formatDuration(att.duration_seconds)}</td>
                  <td>{att.completed_at ? formatDate(att.completed_at) : formatDate(att.started_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
