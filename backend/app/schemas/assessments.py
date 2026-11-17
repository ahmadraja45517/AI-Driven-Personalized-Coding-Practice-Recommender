from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AssessmentKind, AttemptStatus, Difficulty, StudentLevel


class AssessmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: AssessmentKind
    title: str
    description: str | None
    target_level: StudentLevel | None
    section_id: int | None
    total_marks: int
    pass_ratio: float
    duration_minutes: int | None
    attempts_count: int
    best_pct: float | None
    latest_pct: float | None
    passed: bool


# -------- student-facing question (no answers) --------

class OptionForStudent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_index: int
    text: str


class QuestionForStudent(BaseModel):
    id: int
    order_index: int
    topic: str
    difficulty: Difficulty
    text: str
    marks: int
    options: list[OptionForStudent]


class AssessmentForStudent(BaseModel):
    id: int
    kind: AssessmentKind
    title: str
    description: str | None
    total_marks: int
    pass_ratio: float
    duration_minutes: int | None
    questions: list[QuestionForStudent]


# -------- submission --------

class AnswerSubmission(BaseModel):
    question_id: int
    option_id: int


class AssessmentSubmitRequest(BaseModel):
    answers: list[AnswerSubmission] = Field(default_factory=list)


class TopicResult(BaseModel):
    topic: str
    questions_total: int
    questions_correct: int
    accuracy: float


class DifficultyResult(BaseModel):
    difficulty: Difficulty
    questions_total: int
    questions_correct: int
    accuracy: float


class QuestionResult(BaseModel):
    question_id: int
    topic: str
    difficulty: Difficulty
    selected_option_id: int | None
    correct_option_id: int
    is_correct: bool
    explanation: str


class AttemptResult(BaseModel):
    attempt_id: int
    assessment_id: int
    attempt_number: int
    status: AttemptStatus
    score_marks: float
    total_marks: float
    percentage: float
    passed: bool
    submitted_at: datetime | None
    topic_results: list[TopicResult]
    difficulty_results: list[DifficultyResult]
    question_results: list[QuestionResult]


class AttemptHistoryItem(BaseModel):
    attempt_id: int
    attempt_number: int
    score_marks: float
    total_marks: float
    percentage: float
    passed: bool
    submitted_at: datetime | None