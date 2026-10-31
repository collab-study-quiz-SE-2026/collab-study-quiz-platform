import { useEffect, useState } from "react";

const defaultApiUrl = window.location.protocol === "https:" ? "/api" : "http://127.0.0.1:8000";
const apiUrl = (import.meta.env.VITE_API_URL || defaultApiUrl).replace(/\/$/, "");

type Connection = "checking" | "connected" | "unavailable";

export default function App() {
  const [connection, setConnection] = useState<Connection>("checking");

  async function checkConnection() {
    setConnection("checking");
    try {
      const response = await fetch(`${apiUrl}/health`, {
        signal: AbortSignal.timeout(5000),
      });
      if (!response.ok || (await response.json()).status !== "ok") {
        throw new Error("Health check failed");
      }
      setConnection("connected");
    } catch {
      setConnection("unavailable");
    }
  }

  useEffect(() => {
    void checkConnection();
  }, []);

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
        <p>
          {connection === "unavailable"
            ? "Start FastAPI and check your API URL, then try again."
            : "This page checks that the frontend can reach FastAPI."}
        </p>
        <p className="api-url">API: <code>{apiUrl}</code></p>
        <button onClick={() => void checkConnection()} disabled={connection === "checking"}>
          Check connection
        </button>
      </section>

      <p className="footer">The project foundation is ready for the next features.</p>
    </main>
  );
}
