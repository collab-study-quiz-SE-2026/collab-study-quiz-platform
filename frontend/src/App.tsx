import { FormEvent, useEffect, useState } from "react";

const defaultApiUrl = window.location.protocol === "https:" ? "/api" : "http://127.0.0.1:8000";
const apiUrl = (import.meta.env.VITE_API_URL || defaultApiUrl).replace(/\/$/, "");

type Connection = "checking" | "connected" | "unavailable";
type AuthMode = "login" | "register";
type Account = { id: number; email: string; role: string };

async function responseMessage(response: Response) {
  const body = await response.json().catch(() => ({}));
  return body.detail || body.message || "Something went wrong. Please try again.";
}

export default function App() {
  const [connection, setConnection] = useState<Connection>("checking");
  const [mode, setMode] = useState<AuthMode>("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [account, setAccount] = useState<Account | null>(null);
  const [token, setToken] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function checkConnection() {
    setConnection("checking");
    try {
      const response = await fetch(`${apiUrl}/health`, { signal: AbortSignal.timeout(5000) });
      if (!response.ok || (await response.json()).status !== "ok") throw new Error();
      setConnection("connected");
    } catch {
      setConnection("unavailable");
    }
  }

  async function loadAccount(accessToken: string) {
    const response = await fetch(`${apiUrl}/auth/me`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!response.ok) {
      sessionStorage.removeItem("csmqp_access_token");
      setToken("");
      setAccount(null);
      return;
    }
    setAccount(await response.json());
  }

  useEffect(() => {
    void checkConnection();
    const savedToken = sessionStorage.getItem("csmqp_access_token");
    if (savedToken) {
      setToken(savedToken);
      void loadAccount(savedToken);
    }
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage("");
    try {
      const response = await fetch(`${apiUrl}/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) {
        setMessage(await responseMessage(response));
        return;
      }
      if (mode === "register") {
        setMessage("Registration successful. You can now log in.");
        setMode("login");
        setPassword("");
        return;
      }

      const result = await response.json();
      sessionStorage.setItem("csmqp_access_token", result.access_token);
      setToken(result.access_token);
      setPassword("");
      await loadAccount(result.access_token);
      setMessage("Logged in successfully.");
    } catch {
      setMessage("The backend could not be reached. Check the connection and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  async function logout() {
    const response = await fetch(`${apiUrl}/auth/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }).catch(() => null);
    if (!response?.ok) {
      setMessage("Logout could not be confirmed. Keep this tab open and try again.");
      return;
    }
    sessionStorage.removeItem("csmqp_access_token");
    setToken("");
    setAccount(null);
    setMessage("Logged out successfully.");
  }

  return (
    <main>
      <p className="eyebrow">SOFTWARE ENGINEERING PROJECT</p>
      <h1>CSMQP</h1>
      <p className="intro">Collaborative Study Material &amp; Quiz Platform</p>

      <section aria-labelledby="connection-title">
        <h2 id="connection-title">Development connection check</h2>
        <p className={`status ${connection}`} role="status" aria-live="polite">
          <span className="dot" aria-hidden="true" />
          {connection === "checking" && "Checking backend…"}
          {connection === "connected" && "Backend connected"}
          {connection === "unavailable" && "Backend unavailable"}
        </p>
        <p>{connection === "unavailable" ? "Start FastAPI and check your API URL, then try again." : "This page checks that the frontend can reach FastAPI."}</p>
        <p className="api-url">API: <code>{apiUrl}</code></p>
        <button onClick={() => void checkConnection()} disabled={connection === "checking"}>Check connection</button>
      </section>

      <section aria-labelledby="account-title">
        <h2 id="account-title">Account</h2>
        {account ? (
          <div>
            <p>You are logged in as <strong>{account.email}</strong> ({account.role}).</p>
            <button onClick={() => void logout()}>Log out</button>
          </div>
        ) : (
          <form onSubmit={submit}>
            <div className="mode-buttons" aria-label="Account action">
              <button type="button" className={mode === "register" ? "selected" : "secondary"} onClick={() => setMode("register")}>Register</button>
              <button type="button" className={mode === "login" ? "selected" : "secondary"} onClick={() => setMode("login")}>Log in</button>
            </div>
            <label htmlFor="email">Email</label>
            <input id="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
            <label htmlFor="password">Password</label>
            <input id="password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={8} maxLength={72} required />
            <button type="submit" disabled={submitting}>{submitting ? "Please wait…" : mode === "register" ? "Create account" : "Log in"}</button>
          </form>
        )}
        {message && <p className="message" role="status">{message}</p>}
      </section>

      <p className="footer">Authentication is available locally. Future study features will use this signed-in session.</p>
    </main>
  );
}
