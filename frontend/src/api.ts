import {
  Account,
  CategorySummary,
  Question,
  QuestionCreatePayload,
  Quiz,
  QuizCreatePayload,
  QuizAttempt,
  QuizAttemptHistory,
  StudyMaterial,
} from "./types";

const defaultApiUrl =
  window.location.protocol === "https:" ? "/api" : "http://127.0.0.1:8000";
export const API_URL = (
  import.meta.env.VITE_API_URL || defaultApiUrl
).replace(/\/$/, "");

const TOKEN_KEY = "csmqp_access_token";

export function getAuthToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setAuthToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearAuthToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

export function connectToQuizRoom(roomCode: string): WebSocket {
  const token = getAuthToken();
  if (!token) {
    throw new Error("Log in before joining a live quiz room.");
  }

  const apiBase = new URL(API_URL, window.location.href);
  const socketUrl = new URL(
    `/ws/quizzes/${encodeURIComponent(roomCode.trim().toUpperCase())}`,
    apiBase.origin,
  );
  socketUrl.protocol = apiBase.protocol === "https:" ? "wss:" : "ws:";

  return new WebSocket(socketUrl, ["csmqp.v1", `bearer.${token}`]);
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    let message = `Request failed with status ${res.status}`;
    if (typeof errorBody.detail === "string") {
      message = errorBody.detail;
    } else if (Array.isArray(errorBody.detail)) {
      message = errorBody.detail
        .map((e: { msg?: string }) => e.msg || JSON.stringify(e))
        .join(", ");
    } else if (errorBody.message) {
      message = String(errorBody.message);
    }
    throw new Error(message);
  }
  if (res.status === 204) {
    return {} as T;
  }
  return res.json();
}

function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

// ==================== Health Check ====================
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/health`, {
      signal: AbortSignal.timeout(4000),
    });
    if (!res.ok) return false;
    const body = await res.json();
    return body.status === "ok";
  } catch {
    return false;
  }
}

// ==================== Auth ====================
export async function registerUser(email: string, password: string): Promise<{ message: string }> {
  const res = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return handleResponse(res);
}

export async function loginUser(
  email: string,
  password: string
): Promise<{ access_token: string; token_type: string }> {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return handleResponse(res);
}

export async function logoutUser(): Promise<void> {
  const token = getAuthToken();
  if (token) {
    await fetch(`${API_URL}/auth/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }).catch(() => null);
  }
  clearAuthToken();
}

export async function getMe(): Promise<Account> {
  const res = await fetch(`${API_URL}/auth/me`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

// ==================== Question Bank ====================
export async function listQuestions(params?: {
  subject?: string;
  topic?: string;
  difficulty?: string;
}): Promise<Question[]> {
  const query = new URLSearchParams();
  if (params?.subject) query.set("subject", params.subject);
  if (params?.topic) query.set("topic", params.topic);
  if (params?.difficulty) query.set("difficulty", params.difficulty);

  const url = `${API_URL}/questions${query.toString() ? `?${query.toString()}` : ""}`;
  const res = await fetch(url, { headers: authHeaders() });
  return handleResponse(res);
}

export async function getQuestionCategories(): Promise<CategorySummary> {
  const res = await fetch(`${API_URL}/questions/categories`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function getMyQuestions(): Promise<Question[]> {
  const res = await fetch(`${API_URL}/questions/me`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function createQuestion(payload: QuestionCreatePayload): Promise<Question> {
  const res = await fetch(`${API_URL}/questions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}

export async function updateQuestion(
  id: number,
  payload: Partial<QuestionCreatePayload>
): Promise<Question> {
  const res = await fetch(`${API_URL}/questions/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}

export async function deleteQuestion(id: number): Promise<void> {
  const res = await fetch(`${API_URL}/questions/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  return handleResponse(res);
}

// Moderation
export async function getModerationQueue(statusFilter?: string): Promise<Question[]> {
  const query = new URLSearchParams();
  if (statusFilter) query.set("status_filter", statusFilter);
  const url = `${API_URL}/moderation/questions${query.toString() ? `?${query.toString()}` : ""}`;
  const res = await fetch(url, { headers: authHeaders() });
  return handleResponse(res);
}

export async function approveQuestion(id: number): Promise<Question> {
  const res = await fetch(`${API_URL}/questions/${id}/approve`, {
    method: "POST",
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function rejectQuestion(id: number, comment?: string): Promise<Question> {
  const query = comment ? `?comment=${encodeURIComponent(comment)}` : "";
  const res = await fetch(`${API_URL}/questions/${id}/reject${query}`, {
    method: "POST",
    headers: authHeaders(),
  });
  return handleResponse(res);
}

// ==================== Quizzes ====================
export async function listQuizzes(): Promise<Quiz[]> {
  const res = await fetch(`${API_URL}/quizzes`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function getQuiz(id: number): Promise<Quiz> {
  const res = await fetch(`${API_URL}/quizzes/${id}`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function createQuiz(payload: QuizCreatePayload): Promise<Quiz> {
  const res = await fetch(`${API_URL}/quizzes`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}

export async function joinQuizByRoom(roomCode: string): Promise<QuizAttempt> {
  const res = await fetch(`${API_URL}/quizzes/join/${encodeURIComponent(roomCode.trim().toUpperCase())}`, {
    method: "POST",
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function startQuizSession(quizId: number): Promise<QuizAttempt> {
  const res = await fetch(`${API_URL}/quizzes/${quizId}/sessions`, {
    method: "POST",
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function submitQuizAnswer(
  attemptId: number,
  questionId: number,
  answerIndex: number,
  timeSpentSeconds: number
): Promise<QuizAttempt> {
  const res = await fetch(`${API_URL}/quiz-sessions/${attemptId}/answers`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify({
      question_id: questionId,
      answer_index: answerIndex,
      time_spent_seconds: timeSpentSeconds,
    }),
  });
  return handleResponse(res);
}

export async function completeQuizSession(attemptId: number): Promise<QuizAttempt> {
  const res = await fetch(`${API_URL}/quiz-sessions/${attemptId}/complete`, {
    method: "POST",
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function getMyAttemptHistory(): Promise<QuizAttemptHistory[]> {
  const res = await fetch(`${API_URL}/quiz-attempts/me`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

// ==================== Study Materials ====================
export async function listStudyMaterials(params?: {
  search?: string;
  subject?: string;
  topic?: string;
  tag?: string;
}): Promise<StudyMaterial[]> {
  const query = new URLSearchParams();
  if (params?.search) query.set("search", params.search);
  if (params?.subject) query.set("subject", params.subject);
  if (params?.topic) query.set("topic", params.topic);
  if (params?.tag) query.set("tag", params.tag);

  const url = `${API_URL}/materials${query.toString() ? `?${query.toString()}` : ""}`;
  const res = await fetch(url, { headers: authHeaders() });
  return handleResponse(res);
}

export async function uploadStudyMaterial(formData: FormData): Promise<StudyMaterial> {
  const res = await fetch(`${API_URL}/materials/upload`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });
  return handleResponse(res);
}

export async function downloadStudyMaterialFile(
  materialId: number,
  fileName: string
): Promise<void> {
  const res = await fetch(`${API_URL}/materials/${materialId}/download`, {
    headers: authHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Download failed with status ${res.status}`);
  }
  const blob = await res.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = downloadUrl;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(downloadUrl);
}
