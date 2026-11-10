import { FormEvent, useEffect, useState } from "react";
import { Account, ConnectionStatus } from "./types";
import {
  checkBackendHealth,
  getMe,
  loginUser,
  logoutUser,
  registerUser,
  setAuthToken,
  getAuthToken,
} from "./api";
import QuestionBank from "./components/QuestionBank";
import Quizzes from "./components/Quizzes";
import StudyMaterials from "./components/StudyMaterials";
import AttemptHistory from "./components/AttemptHistory";
import ModeratorQueue from "./components/ModeratorQueue";
import Analytics from "./components/Analytics";

type MainNavTab = "questions" | "quizzes" | "materials" | "history" | "moderation" | "analytics";
type AuthMode = "login" | "register";

export default function App() {
  const [connection, setConnection] = useState<ConnectionStatus>("checking");
  const [account, setAccount] = useState<Account | null>(null);
  const [navTab, setNavTab] = useState<MainNavTab>("questions");

  // Auth form state
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authMessage, setAuthMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);
  const [submittingAuth, setSubmittingAuth] = useState(false);

  async function checkConnection() {
    setConnection("checking");
    const ok = await checkBackendHealth();
    setConnection(ok ? "connected" : "unavailable");
  }

  async function loadCurrentAccount() {
    const token = getAuthToken();
    if (!token) {
      setAccount(null);
      return;
    }
    try {
      const me = await getMe();
      setAccount(me);
    } catch {
      logoutUser();
      setAccount(null);
    }
  }

  useEffect(() => {
    void checkConnection();
    void loadCurrentAccount();
  }, []);

  async function handleAuthSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmittingAuth(true);
    setAuthMessage(null);
    try {
      if (authMode === "register") {
        await registerUser(email, password);
        setAuthMessage({
          text: "Registration successful! You can now log in.",
          type: "success",
        });
        setAuthMode("login");
      } else {
        const res = await loginUser(email, password);
        setAuthToken(res.access_token);
        setPassword("");
        await loadCurrentAccount();
        setAuthMessage({ text: "Logged in successfully!", type: "success" });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Authentication failed";
      setAuthMessage({ text: msg, type: "error" });
    } finally {
      setSubmittingAuth(false);
    }
  }

  async function handleLogout() {
    await logoutUser();
    setAccount(null);
    setNavTab("questions");
    setAuthMessage({ text: "Logged out successfully.", type: "success" });
  }

  return (
    <div className="app-layout">
      {/* ================= TOP NAVBAR ================= */}
      <header className="navbar">
        <div className="nav-brand">
          <span className="brand-badge">CSMQP</span>
          <span className="brand-title">Collaborative Study &amp; Quiz Platform</span>
        </div>

        <div className="nav-right">
          {/* Health indicator */}
          <button
            type="button"
            className={`status-pill status-${connection}`}
            onClick={() => void checkConnection()}
            title="Click to re-check backend connection"
          >
            <span className="dot" aria-hidden="true" />
            {connection === "connected" && "Backend Connected"}
            {connection === "checking" && "Connecting…"}
            {connection === "unavailable" && "Backend Offline"}
          </button>

          {/* Account information */}
          {account ? (
            <div className="user-profile-widget">
              <span className="user-email">{account.email}</span>
              <span className={`role-badge role-${account.role}`}>{account.role}</span>
              <button
                type="button"
                className="small-btn secondary"
                onClick={handleLogout}
              >
                Log Out
              </button>
            </div>
          ) : (
            <span className="auth-hint">Please sign in below</span>
          )}
        </div>
      </header>

      {/* ================= MAIN CONTENT ================= */}
      <main className="content-container">
        {!account ? (
          /* ================= LOGIN / REGISTER VIEW ================= */
          <div className="auth-landing-card">
            <div className="auth-header">
              <h1>Welcome to CSMQP</h1>
              <p className="intro">
                A collaborative academic platform for students to share study materials, contribute question banks, and participate in quizzes.
              </p>
            </div>

            {authMessage && (
              <div className={`banner-alert ${authMessage.type === "success" ? "banner-success" : "banner-error"}`}>
                {authMessage.text}
              </div>
            )}

            <div className="auth-form-wrapper">
              <div className="mode-buttons" aria-label="Account action">
                <button
                  type="button"
                  className={authMode === "login" ? "selected" : "secondary"}
                  onClick={() => { setAuthMode("login"); setAuthMessage(null); }}
                >
                  Log In
                </button>
                <button
                  type="button"
                  className={authMode === "register" ? "selected" : "secondary"}
                  onClick={() => { setAuthMode("register"); setAuthMessage(null); }}
                >
                  Create Account
                </button>
              </div>

              <form onSubmit={handleAuthSubmit}>
                <label htmlFor="auth-email">Email Address</label>
                <input
                  id="auth-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                />

                <label htmlFor="auth-pass">Password (min 8 characters)</label>
                <input
                  id="auth-pass"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  minLength={8}
                  maxLength={72}
                  required
                />

                <button type="submit" disabled={submittingAuth}>
                  {submittingAuth
                    ? "Processing…"
                    : authMode === "login"
                    ? "Log In to Account"
                    : "Create Student Account"}
                </button>
              </form>


            </div>
          </div>
        ) : (
          /* ================= AUTHENTICATED WORKSPACE ================= */
          <div>
            {/* Main Navigation Bar */}
            <nav className="main-nav-tabs" aria-label="Platform navigation">
              <button
                type="button"
                className={`nav-tab-item ${navTab === "questions" ? "active" : ""}`}
                onClick={() => setNavTab("questions")}
              >
                📚 Question Bank
              </button>
              <button
                type="button"
                className={`nav-tab-item ${navTab === "quizzes" ? "active" : ""}`}
                onClick={() => setNavTab("quizzes")}
              >
                🎯 Quizzes &amp; Rooms
              </button>
              <button
                type="button"
                className={`nav-tab-item ${navTab === "materials" ? "active" : ""}`}
                onClick={() => setNavTab("materials")}
              >
                📁 Study Materials
              </button>
              <button
                type="button"
                className={`nav-tab-item ${navTab === "history" ? "active" : ""}`}
                onClick={() => setNavTab("history")}
              >
                📊 Attempt History
              </button>
              <button type="button" className={navTab === "analytics" ? "nav-tab-item active" : "nav-tab-item"} onClick={() => setNavTab("analytics")}>Analytics</button>
              {account.role === "moderator" && (
                <button
                  type="button"
                  className={`nav-tab-item ${navTab === "moderation" ? "active" : ""}`}
                  onClick={() => setNavTab("moderation")}
                >
                  🛡️ Moderation Queue
                </button>
              )}
            </nav>

            {/* Render Selected Feature Tab */}
            <div className="tab-viewport">
              {navTab === "questions" && <QuestionBank />}
              {navTab === "quizzes" && <Quizzes />}
              {navTab === "materials" && <StudyMaterials />}
              {navTab === "history" && <AttemptHistory />}
              {navTab === "analytics" && <Analytics key={account.id} />}
              {navTab === "moderation" && <ModeratorQueue />}
            </div>
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>CSMQP Software Engineering Project • 3-Tier Architecture • FastAPI, React, PostgreSQL 15, S3 Storage</p>
      </footer>
    </div>
  );
}
