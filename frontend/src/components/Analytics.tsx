import { useEffect, useState } from "react";
import { API_URL, getAuthToken } from "../api";
import LearningProgressChart from "./LearningProgressChart";

interface Dashboard {
  total_quizzes_attempted: number;
  average_score: number | null;
  average_time_per_question_seconds: number | null;
  cohort_percentile: number | null;
  topic_accuracy: { topic: string; answered_questions: number; correct_answers: number; accuracy_percentage: number }[];
  recent_results: { attempt_id: number; quiz_title: string; score: number; completed_at: string }[];
}

interface Topic {
  subject: string;
  topic: string;
  total_questions: number;
  correct_answers: number;
  accuracy_percentage: number;
  average_time_seconds: number | null;
  cohort_percentile: number | null;
  strength_level: string;
}

interface Topics {
  total_quizzes_evaluated: number;
  total_questions_evaluated: number;
  topics: Topic[];
}

const numberText = (value: number | null, unit = "") =>
  value === null ? "Not available" : value.toFixed(1) + unit;

export default function Analytics() {
  const [view, setView] = useState("dashboard");
  const [refresh, setRefresh] = useState(0);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [topics, setTopics] = useState<Topics | null>(null);
  const [subject, setSubject] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const token = getAuthToken();

  useEffect(() => {
    if (view === "progress") return;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    const route = view === "dashboard" ? "/dashboard/performance" : "/analytics/topics";
    fetch(API_URL + route, {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    }).then(async response => {
      if (!response.ok) throw new Error(`Unable to load analytics (${response.status}). Please retry or sign in again.`);
      return response.json();
    }).then(data => {
      if (view === "dashboard") setDashboard(data);
      else setTopics(data);
    }).catch(error => {
      if (!controller.signal.aborted) setError(error.message);
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [view, refresh, token]);

  const filteredTopics = topics?.topics.filter(t => !subject || t.subject === subject) ?? [];
  return (
    <section className="analytics-panel" aria-label="Your analytics">
      <h2>Your analytics</h2>
      <div className="analytics-controls">
        {["dashboard", "topics", "progress"].map(tab =>
          <button key={tab} type="button" aria-pressed={view === tab} className={view === tab ? "" : "secondary"} onClick={() => setView(tab)}>
            {tab === "dashboard" ? "Overview" : tab === "topics" ? "Topic performance" : "Learning progress"}
          </button>
        )}
        <button type="button" className="secondary" onClick={() => setRefresh(value => value + 1)}>Refresh</button>
      </div>
      {view === "progress" ? (
        <LearningProgressChart key={refresh} apiUrl={API_URL} token={token ?? ""} />
      ) : loading ? <p role="status">Loading analytics…</p> : error ? <p role="alert">{error}</p> : (
        <>
          {view === "dashboard" && dashboard && (
            <>
              <dl className="analytics-summary">
                <div><dt>Quizzes attempted</dt><dd>{dashboard.total_quizzes_attempted}</dd></div>
                <div><dt>Average score</dt><dd>{numberText(dashboard.average_score, "%")}</dd></div>
                <div><dt>Average time per question</dt><dd>{numberText(dashboard.average_time_per_question_seconds, " s")}</dd></div>
                <div><dt>Cohort percentile</dt><dd>{numberText(dashboard.cohort_percentile)}</dd></div>
              </dl>
              <h3>Recent results</h3>
              {dashboard.recent_results.length === 0 ? <p>Complete a quiz to see your results here.</p> :
                <div className="analytics-table"><table><thead><tr><th>Quiz</th><th>Score</th><th>Completed</th></tr></thead><tbody>
                  {dashboard.recent_results.map(result => <tr key={result.attempt_id}><td>{result.quiz_title}</td><td>{result.score}%</td><td>{new Date(result.completed_at).toLocaleString()}</td></tr>)}
                </tbody></table></div>}
              <h3>Topic accuracy</h3>
              {dashboard.topic_accuracy.length === 0 ? <p>No answered questions yet.</p> :
                <ul>{dashboard.topic_accuracy.map(topic => <li key={topic.topic}>{topic.topic} — {topic.correct_answers}/{topic.answered_questions} correct ({numberText(topic.accuracy_percentage, "%")})</li>)}</ul>}
            </>
          )}
          {view === "topics" && topics && (
            <>
              <p>{topics.total_quizzes_evaluated} quizzes and {topics.total_questions_evaluated} questions evaluated.</p>
              <label htmlFor="analytics-subject">Subject</label>
              <select id="analytics-subject" value={subject} onChange={event => setSubject(event.target.value)}>
                <option value="">All subjects</option>
                {[...new Set(topics.topics.map(topic => topic.subject))].sort().map(value => <option key={value}>{value}</option>)}
              </select>
              {filteredTopics.length === 0 ? <p>No topic results for this selection. Complete a quiz to build your topic history.</p> :
                <div className="analytics-table"><table><thead><tr><th>Subject / topic</th><th>Correct</th><th>Accuracy</th><th>Average time</th><th>Percentile</th><th>Strength</th></tr></thead><tbody>
                  {filteredTopics.map(topic => <tr key={JSON.stringify([topic.subject, topic.topic])}>
                    <td>{topic.subject} / {topic.topic}</td><td>{topic.correct_answers}/{topic.total_questions}</td><td>{numberText(topic.accuracy_percentage, "%")}</td><td>{numberText(topic.average_time_seconds, " s")}</td><td>{numberText(topic.cohort_percentile)}</td><td>{topic.strength_level}</td>
                  </tr>)}
                </tbody></table></div>}
            </>
          )}
        </>
      )}
    </section>
  );
}
