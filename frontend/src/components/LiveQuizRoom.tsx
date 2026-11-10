import { useCallback, useEffect, useRef, useState } from "react";
import { connectToQuizRoom } from "../api";

type RoomRole = "host" | "participant";
type ConnectionState = "connecting" | "connected" | "disconnected";

interface LiveQuestion {
  question_id: number;
  question_text: string;
  options: string[];
  question_number: number;
  total_questions: number;
  duration_seconds: number;
  deadline: string;
}

interface RoundStanding {
  student_id: number;
  score: number;
  correct_answers: number;
}

interface RoundResult {
  question_id: number;
  correct_answer_index: number;
  explanation: string | null;
  standings: RoundStanding[];
  quiz_complete: boolean;
}

interface LiveQuizRoomProps {
  roomCode: string;
  onLeave: () => void;
}

export default function LiveQuizRoom({ roomCode, onLeave }: LiveQuizRoomProps) {
  const socketRef = useRef<WebSocket | null>(null);
  const leavingRef = useRef(false);
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const [role, setRole] = useState<RoomRole | null>(null);
  const [quizTitle, setQuizTitle] = useState("");
  const [questionCount, setQuestionCount] = useState(0);
  const [question, setQuestion] = useState<LiveQuestion | null>(null);
  const [roundResult, setRoundResult] = useState<RoundResult | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [answeredCount, setAnsweredCount] = useState(0);
  const [participantCount, setParticipantCount] = useState(0);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [error, setError] = useState("");

  const connect = useCallback(() => {
    const previous = socketRef.current;
    if (
      previous &&
      (previous.readyState === WebSocket.CONNECTING ||
        previous.readyState === WebSocket.OPEN)
    ) {
      return;
    }

    leavingRef.current = false;
    setConnection("connecting");
    setRole(null);
    setError("");

    let socket: WebSocket;
    try {
      socket = connectToQuizRoom(roomCode);
    } catch (connectionError) {
      setConnection("disconnected");
      setError(
        connectionError instanceof Error
          ? connectionError.message
          : "Could not connect to the live room.",
      );
      return;
    }

    socketRef.current = socket;
    socket.onopen = () => setConnection("connected");
    socket.onmessage = (event: MessageEvent<string>) => {
      let message: Record<string, unknown>;
      try {
        message = JSON.parse(event.data) as Record<string, unknown>;
      } catch {
        setError("The server sent an unreadable room message.");
        return;
      }

      if (message.type === "ROOM_JOINED") {
        setRole(message.role === "host" ? "host" : "participant");
        setQuizTitle(typeof message.quiz_title === "string" ? message.quiz_title : "Live quiz");
        setQuestionCount(typeof message.question_count === "number" ? message.question_count : 0);
      } else if (message.type === "QUESTION_OPEN") {
        setQuestion(message as unknown as LiveQuestion);
        setRoundResult(null);
        setSelectedAnswer(null);
        setSubmitted(false);
        setAnsweredCount(0);
        setParticipantCount(0);
        setError("");
      } else if (message.type === "ANSWER_STATE") {
        setAnsweredCount(typeof message.answered_count === "number" ? message.answered_count : 0);
        setParticipantCount(typeof message.participant_count === "number" ? message.participant_count : 0);
      } else if (message.type === "ROUND_END") {
        setRoundResult(message as unknown as RoundResult);
        setSubmitted(true);
      } else if (message.type === "ERROR") {
        setError(typeof message.message === "string" ? message.message : "The server rejected that action.");
      }
    };
    socket.onerror = () => {
      if (socketRef.current === socket) {
        setError("Could not connect to the live room. Check that the backend is running.");
      }
    };
    socket.onclose = () => {
      if (socketRef.current === socket && !leavingRef.current) {
        setConnection("disconnected");
        setError("The room connection closed. You can try reconnecting.");
      }
    };
  }, [roomCode]);

  useEffect(() => {
    connect();
    return () => {
      leavingRef.current = true;
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [connect]);

  useEffect(() => {
    if (!question || roundResult) return;
    const updateCountdown = () => {
      const remaining = Math.ceil((Date.parse(question.deadline) - Date.now()) / 1000);
      setSecondsLeft(Math.max(0, remaining));
    };
    updateCountdown();
    const timer = window.setInterval(updateCountdown, 250);
    return () => window.clearInterval(timer);
  }, [question, roundResult]);

  function send(message: Record<string, unknown>) {
    const socket = socketRef.current;
    if (socket?.readyState !== WebSocket.OPEN) {
      setError("You are disconnected from the room. Reconnect before continuing.");
      return false;
    }
    socket.send(JSON.stringify(message));
    return true;
  }

  function startRound() {
    setError("");
    send({ type: "START_QUIZ" });
  }

  function submitAnswer() {
    if (!question || selectedAnswer === null) {
      setError("Choose an answer before submitting.");
      return;
    }
    if (send({ type: "SUBMIT_ANSWER", question_id: question.question_id, answer_index: selectedAnswer })) {
      setSubmitted(true);
      setError("");
    }
  }

  function leaveRoom() {
    leavingRef.current = true;
    socketRef.current?.close();
    socketRef.current = null;
    onLeave();
  }

  return (
    <section className="feature-container" aria-labelledby="live-room-title">
      <div className="section-header">
        <div>
          <h2 id="live-room-title">{quizTitle || "Live quiz room"}</h2>
          <p className="subtitle">Room code: <strong>{roomCode}</strong></p>
        </div>
        <div>
          <span className={`status-pill status-${connection}`} role="status">
            {connection === "connected" ? "Room connected" : connection === "connecting" ? "Connecting…" : "Disconnected"}
          </span>{" "}
          <button type="button" className="secondary" onClick={leaveRoom}>Leave room</button>
        </div>
      </div>

      {error && <p className="banner-alert banner-error" role="alert">{error}</p>}

      {connection === "disconnected" && (
        <button type="button" onClick={connect}>Reconnect</button>
      )}

      {connection === "connected" && role && !question && !roundResult && (
        role === "host" ? (
          <div className="empty-state">
            <p>Connected as host. Participants must join this room before you start a round.</p>
            <button type="button" onClick={startRound}>Start {questionCount ? "first" : "a"} question</button>
          </div>
        ) : (
          <div className="empty-state"><p>Connected as a participant. Waiting for the host to start the quiz…</p></div>
        )
      )}

      {question && !roundResult && (
        <div className="quiz-player-card">
          <div className="quiz-player-header">
            <div>
              <h3>Question {question.question_number} of {question.total_questions}</h3>
              <p className="subtext">{role === "host" ? "Host view" : "Select an answer before the timer ends."}</p>
            </div>
            <div className="quiz-timer-badge" role="timer">{secondsLeft}s remaining</div>
          </div>
          <div className="quiz-question-body">
            <h4 className="player-prompt">{question.question_text}</h4>
            <div className="player-options-list">
              {question.options.map((option, index) => (
                role === "participant" ? (
                  <button
                    key={index}
                    type="button"
                    className={`quiz-choice-btn ${selectedAnswer === index ? "selected" : ""}`}
                    onClick={() => setSelectedAnswer(index)}
                    disabled={submitted || secondsLeft === 0}
                  >
                    <span className="choice-badge">{String.fromCharCode(65 + index)}</span>
                    <span className="choice-text">{option}</span>
                  </button>
                ) : (
                  <div key={index} className="option-row">
                    <span className="option-letter">{String.fromCharCode(65 + index)}</span>
                    <span>{option}</span>
                  </div>
                )
              ))}
            </div>
          </div>
          {role === "participant" && (
            <div className="quiz-player-footer">
              {submitted ? (
                <p role="status">Answer submitted. Waiting for the round to end…</p>
              ) : (
                <button type="button" onClick={submitAnswer} disabled={selectedAnswer === null || secondsLeft === 0}>
                  Submit answer
                </button>
              )}
              {participantCount > 0 && <p role="status">{answeredCount} of {participantCount} participants answered.</p>}
            </div>
          )}
        </div>
      )}

      {roundResult && (
        <div className="result-card">
          <h3>{roundResult.quiz_complete ? "Quiz complete" : "Round complete"}</h3>
          <p><strong>Correct answer:</strong> {question?.options[roundResult.correct_answer_index] ?? "Unavailable"}</p>
          {roundResult.explanation && <p>{roundResult.explanation}</p>}
          <h4>Standings</h4>
          {roundResult.standings.length === 0 ? (
            <p>No participant results were recorded for this round.</p>
          ) : (
            <ol>
              {roundResult.standings.map((standing) => (
                <li key={standing.student_id}>
                  Student #{standing.student_id}: {standing.correct_answers} correct, {standing.score}%
                </li>
              ))}
            </ol>
          )}
          {roundResult.quiz_complete ? (
            <button type="button" onClick={leaveRoom}>Finish</button>
          ) : role === "host" ? (
            <button type="button" onClick={startRound}>Start next question</button>
          ) : (
            <p role="status">Waiting for the host to start the next question…</p>
          )}
        </div>
      )}
    </section>
  );
}
