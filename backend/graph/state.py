from typing import List, Optional, TypedDict

from pydantic import BaseModel


class QuizQuestion(BaseModel):
    id: str
    type: str
    stem: str
    options: Optional[List[str]] = None
    correct_index: Optional[int] = None
    explanation: str


class ConfusionEntry(BaseModel):
    question_id: str
    student_answer: str
    correct: bool
    confusion_reason: str


class TutorState(TypedDict):
    session_id: str
    raw_document: str
    lesson_plan: Optional[dict]
    current_lesson_index: int
    current_lesson_content: Optional[dict]
    confusion_log: Optional[dict]
    iteration_count: int
    max_iterations: int
    passed: bool
    agent_log: List[str]
    final_curriculum: Optional[List[dict]]
