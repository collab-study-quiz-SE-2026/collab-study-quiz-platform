export type ConnectionStatus = "checking" | "connected" | "unavailable";

export type UserRole = "student" | "moderator";

export interface Account {
  id: number;
  email: string;
  role: UserRole;
}

export type QuestionStatus = "PENDING" | "APPROVED" | "REJECTED";

export interface Question {
  id: number;
  question_text: string;
  options: string[];
  subject: string;
  topic: string;
  difficulty: "easy" | "medium" | "hard" | string;
  explanation?: string | null;
  status: QuestionStatus;
  creator_id: number;
  moderator_id?: number | null;
  moderation_comment?: string | null;
  created_at: string;
  updated_at: string;
}

export interface QuestionCreatePayload {
  question_text: string;
  options: string[];
  correct_answer_index: number;
  subject: string;
  topic: string;
  difficulty: string;
  explanation?: string;
}

export interface CategorySummary {
  subjects: string[];
  topics: string[];
  difficulties: string[];
}

export interface QuizQuestion {
  id: number;
  question_text: string;
  options: string[];
  subject: string;
  topic: string;
  difficulty: string;
}

export interface Quiz {
  id: number;
  title: string;
  description: string;
  duration_minutes: number;
  max_attempts: number;
  room_code: string;
  status: string;
  host_id: number;
  created_at: string;
  started_at?: string | null;
  questions: QuizQuestion[];
}

export interface QuizCreatePayload {
  title: string;
  description: string;
  duration_minutes: number;
  max_attempts: number;
  question_ids: number[];
}

export interface QuizAttempt {
  id: number;
  quiz_id: number;
  student_id: number;
  status: "active" | "completed" | "expired" | string;
  score?: number | null;
  answers: Record<string, number>;
  question_timings: Record<string, number>;
  started_at: string;
  completed_at?: string | null;
}

export interface QuizAttemptHistory {
  id: number;
  quiz_id: number;
  quiz_title: string;
  student_id: number;
  status: string;
  score?: number | null;
  answers: Record<string, number>;
  question_timings: Record<string, number>;
  started_at: string;
  completed_at?: string | null;
  duration_seconds?: number | null;
}

export interface StudyMaterial {
  id: number;
  title: string;
  course_code: string;
  subject: string;
  topic: string;
  tags: string[];
  file_name: string;
  file_size_bytes: number;
  content_type: string;
  storage_key: string;
  uploader_id: number;
  uploaded_at: string;
}
