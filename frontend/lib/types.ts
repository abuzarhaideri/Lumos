export type LessonSectionType =
  | "explanation"
  | "analogy"
  | "example"
  | "code"
  | "diagram_prompt";

export interface LessonSection {
  type: LessonSectionType;
  title: string;
  body?: string;
  language?: string;
  snippet?: string;
}

export interface QuizQuestion {
  id: string;
  type: "mcq" | "fill_blank" | "short_answer";
  stem: string;
  options?: string[];
  correct_index?: number;
  explanation?: string;
}

export interface LessonQuiz {
  questions: QuizQuestion[];
  pass_threshold: number;
}

export interface LessonContent {
  lesson_id: string;
  sections: LessonSection[];
  quiz: LessonQuiz;
}

export interface StreamEvent {
  id: string;
  agent: "ArchitectAgent" | "ContentAgent" | "StudentAgent" | "System";
  stage: string;
  message: string;
  at: string;
}

export interface SsePayload {
  type: "log" | "done" | "timeout";
  message?: string;
}
