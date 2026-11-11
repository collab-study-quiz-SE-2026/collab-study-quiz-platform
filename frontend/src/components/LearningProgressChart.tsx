import { useEffect, useState } from "react";

export interface LearningProgressPoint {
  attempt_id: number;
  quiz_id: number;
  quiz_title: string;
  completed_at: string;
  score: number;
  accuracy_percentage: number;
  correct_answers: number;
  total_questions: number;
  duration_seconds: number | null;
  moving_average_score: number;
  trajectory: "improving" | "declining" | "stable";
}

export interface TopicProgressPoint {
  completed_at: string;
  quiz_id: number;
  quiz_title: string;
  correct_answers: number;
  total_questions: number;
  accuracy_percentage: number;
}

export interface TopicProgressTrend {
  subject: string;
  topic: string;
  total_attempts: number;
  current_accuracy: number;
  history: TopicProgressPoint[];
}

export interface LearningProgressResponse {
  student_id: number;
  total_quizzes_completed: number;
  average_score: number | null;
  highest_score: number | null;
  lowest_score: number | null;
  initial_score: number | null;
  latest_score: number | null;
  overall_improvement: number | null;
  trend_direction: "improving" | "declining" | "stable" | "insufficient_data";
  timeline: LearningProgressPoint[];
  topic_trends: TopicProgressTrend[];
}

interface LearningProgressChartProps {
  apiUrl: string;
  token: string;
}

export default function LearningProgressChart({ apiUrl, token }: LearningProgressChartProps) {
  const [data, setData] = useState<LearningProgressResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);

  useEffect(() => {
    async function fetchProgress() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`${apiUrl}/analytics/progress`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) {
          throw new Error(`Failed to load progress data (${response.status})`);
        }
        const json: LearningProgressResponse = await response.json();
        setData(json);
        if (json.topic_trends.length > 0 && !selectedTopic) {
          setSelectedTopic(JSON.stringify([json.topic_trends[0].subject, json.topic_trends[0].topic]));
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Error loading learning progress");
      } finally {
        setLoading(false);
      }
    }

    if (token) {
      void fetchProgress();
    }
  }, [apiUrl, token]);

  if (loading) {
    return <div className="progress-loading">Loading your learning progress...</div>;
  }

  if (error) {
    return <div className="progress-error">{error}</div>;
  }

  if (!data || data.total_quizzes_completed === 0) {
    return (
      <div className="progress-empty" role="region" aria-label="Learning Progress">
        <h3>Learning Progress &amp; Trends</h3>
        <p>No quiz attempts recorded yet.</p>
        <p className="hint">Complete quizzes to unlock interactive score trajectories, moving averages, and topic mastery trends.</p>
      </div>
    );
  }

  const timeline = data.timeline;
  const chartWidth = 600;
  const chartHeight = 260;
  const padding = { top: 30, right: 30, bottom: 40, left: 45 };

  const innerWidth = chartWidth - padding.left - padding.right;
  const innerHeight = chartHeight - padding.top - padding.bottom;

  const pointsCount = timeline.length;
  const getX = (index: number) => {
    if (pointsCount <= 1) return padding.left + innerWidth / 2;
    return padding.left + (index / (pointsCount - 1)) * innerWidth;
  };

  const getY = (score: number) => {
    return padding.top + innerHeight - (Math.max(0, Math.min(100, score)) / 100) * innerHeight;
  };

  // Score line path
  const scorePath =
    pointsCount > 1
      ? timeline
          .map((pt, i) => `${i === 0 ? "M" : "L"} ${getX(i)} ${getY(pt.score)}`)
          .join(" ")
      : "";

  // Moving average trend line path
  const trendPath =
    pointsCount > 1
      ? timeline
          .map(
            (pt, i) =>
              `${i === 0 ? "M" : "L"} ${getX(i)} ${getY(pt.moving_average_score)}`
          )
          .join(" ")
      : "";

  const activePoint = hoveredIndex !== null ? timeline[hoveredIndex] : null;

  const currentTopicTrend = data.topic_trends.find(
    (t) => JSON.stringify([t.subject, t.topic]) === selectedTopic
  );

  return (
    <div className="learning-progress-dashboard" role="region" aria-label="Learning Progress Dashboard">
      <header className="progress-header">
        <h3>Learning Progress &amp; Score Trends</h3>
        <span className={`trend-badge badge-${data.trend_direction}`}>
          Trend: {data.trend_direction.toUpperCase()}
          {data.trend_direction === "improving" && " ↗"}
          {data.trend_direction === "declining" && " ↘"}
          {data.trend_direction === "stable" && " →"}
        </span>
      </header>

      {/* Summary KPI Cards */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <span className="kpi-label">Quizzes Completed</span>
          <span className="kpi-value">{data.total_quizzes_completed}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Average Score</span>
          <span className="kpi-value">{data.average_score ?? 0}%</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Highest Score</span>
          <span className="kpi-value">{data.highest_score ?? 0}%</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Overall Progress</span>
          <span className="kpi-value">
            {data.overall_improvement !== null && data.overall_improvement > 0 ? "+" : ""}
            {data.overall_improvement ?? 0} pts
          </span>
        </div>
      </div>

      {/* Interactive Chart */}
      <div className="chart-container">
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          className="progress-svg-chart"
          aria-label="Quiz score progress chart"
        >
          {/* Y Axis Grid lines */}
          {[0, 25, 50, 75, 100].map((val) => {
            const y = getY(val);
            return (
              <g key={val} className="grid-line-group">
                <line
                  x1={padding.left}
                  y1={y}
                  x2={chartWidth - padding.right}
                  y2={y}
                  stroke="#e2e8f0"
                  strokeDasharray={val === 0 || val === 100 ? undefined : "3 3"}
                />
                <text
                  x={padding.left - 8}
                  y={y + 4}
                  textAnchor="end"
                  fontSize="10"
                  fill="#64748b"
                >
                  {val}%
                </text>
              </g>
            );
          })}

          {/* Lines */}
          {pointsCount > 1 && (
            <>
              {/* Trend line (Moving Average) */}
              <path
                d={trendPath}
                fill="none"
                stroke="#94a3b8"
                strokeWidth="2"
                strokeDasharray="4 4"
              />
              {/* Actual Score line */}
              <path
                d={scorePath}
                fill="none"
                stroke="#2563eb"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </>
          )}

          {/* Interactive Data Points */}
          {timeline.map((pt, i) => {
            const cx = getX(i);
            const cy = getY(pt.score);
            const isHovered = hoveredIndex === i;
            return (
              <g key={pt.attempt_id}>
                <circle
                  cx={cx}
                  cy={cy}
                  r={isHovered ? 7 : 4}
                  fill={isHovered ? "#1d4ed8" : "#2563eb"}
                  stroke="#ffffff"
                  strokeWidth={2}
                  style={{ cursor: "pointer", transition: "r 0.15s ease" }}
                  tabIndex={0}
                  role="img"
                  aria-label={`${pt.quiz_title}: ${pt.score}%`}
                  onFocus={() => setHoveredIndex(i)}
                  onBlur={() => setHoveredIndex(null)}
                  onMouseEnter={() => setHoveredIndex(i)}
                  onMouseLeave={() => setHoveredIndex(null)}
                />
                <text
                  x={cx}
                  y={chartHeight - 12}
                  textAnchor="middle"
                  fontSize="9"
                  fill="#64748b"
                >
                  Q{i + 1}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Hover Tooltip Card */}
        {activePoint && (
          <div className="chart-tooltip">
            <strong>{activePoint.quiz_title}</strong>
            <div>Score: <span>{activePoint.score}%</span></div>
            <div>Accuracy: <span>{activePoint.accuracy_percentage}% ({activePoint.correct_answers}/{activePoint.total_questions})</span></div>
            <div>Moving Avg: <span>{activePoint.moving_average_score}%</span></div>
            <div>Trajectory: <span className={`traj-${activePoint.trajectory}`}>{activePoint.trajectory}</span></div>
            {activePoint.duration_seconds !== null && (
              <div>Time: <span>{activePoint.duration_seconds}s</span></div>
            )}
            <small>{new Date(activePoint.completed_at).toLocaleDateString()}</small>
          </div>
        )}
      </div>

      {/* Topic-Wise Trends Section */}
      {data.topic_trends.length > 0 && (
        <div className="topic-trends-section">
          <h4>Topic Performance Trends Over Time</h4>
          <div className="topic-tabs">
            {data.topic_trends.map((t) => (
              <button
                key={JSON.stringify([t.subject, t.topic])}
                type="button"
                className={`topic-tab ${selectedTopic === JSON.stringify([t.subject, t.topic]) ? "active" : ""}`}
                onClick={() => setSelectedTopic(JSON.stringify([t.subject, t.topic]))}
              >
                {t.topic} ({t.current_accuracy}%)
              </button>
            ))}
          </div>

          {currentTopicTrend && (
            <div className="topic-trend-card">
              <p>
                <strong>{currentTopicTrend.topic}</strong> (Subject: {currentTopicTrend.subject}) &mdash;{" "}
                {currentTopicTrend.total_attempts} quiz attempt(s), Current Accuracy:{" "}
                <strong>{currentTopicTrend.current_accuracy}%</strong>
              </p>
              <div className="topic-history-list">
                {currentTopicTrend.history.map((h, idx) => (
                  <div key={idx} className="topic-history-item">
                    <span>{h.quiz_title}</span>
                    <span>{h.correct_answers} / {h.total_questions} correct</span>
                    <span className="topic-history-acc">{h.accuracy_percentage}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
