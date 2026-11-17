from __future__ import annotations
from app.services.recommendation_service import generate_recommendations
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Assessment, AssessmentAttempt, AssessmentOption, AssessmentQuestion,
    AttemptTopicResult, LearningSection, RoadmapEnrollment, Topic,
)
from app.models.enums import (
    AssessmentKind, AttemptStatus, Difficulty, EnrollmentStatus, UnlockStatus,
)
from app.models import SectionUnlock, StudentProfile
from app.schemas.assessments import (
    AssessmentForStudent, AssessmentSubmitRequest, AssessmentSummary,
    AttemptHistoryItem, AttemptResult, DifficultyResult,
    OptionForStudent, QuestionForStudent, QuestionResult, TopicResult,
)
from app.services.skill_service import recompute_skill_profile_from_attempt
from app.services.unlock_service import evaluate_section


class AssessmentError(Exception):
    pass


def _enrollment(db: Session, user_id: int) -> RoadmapEnrollment | None:
    return db.execute(
        select(RoadmapEnrollment).where(
            RoadmapEnrollment.user_id == user_id,
            RoadmapEnrollment.status == EnrollmentStatus.ACTIVE,
        )
    ).scalar_one_or_none()


def _has_section_access(db: Session, user_id: int, section_id: int) -> bool:
    if _enrollment(db, user_id) is None:
        return False
    unlock = db.execute(
        select(SectionUnlock).where(
            SectionUnlock.user_id == user_id, SectionUnlock.section_id == section_id,
        )
    ).scalar_one_or_none()
    return unlock is not None and unlock.status in (UnlockStatus.UNLOCKED, UnlockStatus.COMPLETED)


def _attempt_stats(db: Session, user_id: int, assessment_id: int) -> tuple[int, float | None, float | None, bool]:
    rows = db.execute(
        select(AssessmentAttempt.percentage, AssessmentAttempt.passed)
        .where(
            AssessmentAttempt.user_id == user_id,
            AssessmentAttempt.assessment_id == assessment_id,
            AssessmentAttempt.status == AttemptStatus.SUBMITTED,
        )
        .order_by(AssessmentAttempt.submitted_at.asc())
    ).all()
    if not rows:
        return 0, None, None, False
    pcts = [float(p) for p, _ in rows if p is not None]
    passed_any = any(bool(ok) for _, ok in rows)
    return len(rows), max(pcts) if pcts else None, pcts[-1] if pcts else None, passed_any


def list_assessments(db: Session, user_id: int) -> list[AssessmentSummary]:
    profile = db.execute(
        select(StudentProfile).where(StudentProfile.user_id == user_id)
    ).scalar_one_or_none()
    if profile is None or profile.selected_level is None:
        return []

    diagnostics = db.execute(
        select(Assessment).where(
            Assessment.kind == AssessmentKind.DIAGNOSTIC,
            Assessment.target_level == profile.selected_level,
            Assessment.is_active.is_(True),
        )
    ).scalars().all()

    section_ends = db.execute(
        select(Assessment).where(
            Assessment.kind == AssessmentKind.SECTION_END,
            Assessment.is_active.is_(True),
        )
    ).scalars().all()

    visible: list[Assessment] = list(diagnostics)
    for a in section_ends:
        if a.section_id is not None and _has_section_access(db, user_id, a.section_id):
            visible.append(a)

    out: list[AssessmentSummary] = []
    for a in visible:
        attempts_count, best, latest, passed = _attempt_stats(db, user_id, a.id)
        out.append(AssessmentSummary(
            id=a.id, kind=a.kind, title=a.title, description=a.description,
            target_level=a.target_level, section_id=a.section_id,
            total_marks=a.total_marks, pass_ratio=float(a.pass_ratio),
            duration_minutes=a.duration_minutes,
            attempts_count=attempts_count, best_pct=best, latest_pct=latest, passed=passed,
        ))
    return out


def get_assessment_for_student(db: Session, user_id: int, assessment_id: int) -> AssessmentForStudent:
    assessment = db.get(Assessment, assessment_id)
    if assessment is None or not assessment.is_active:
        raise AssessmentError("Assessment not found")

    if assessment.kind == AssessmentKind.DIAGNOSTIC:
        profile = db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        ).scalar_one_or_none()
        if profile is None or profile.selected_level != assessment.target_level:
            raise AssessmentError("You cannot access this diagnostic assessment")
    else:
        if assessment.section_id is None or not _has_section_access(db, user_id, assessment.section_id):
            raise AssessmentError("You cannot access this assessment")

    q_rows = db.execute(
        select(AssessmentQuestion, Topic.code)
        .join(Topic, Topic.id == AssessmentQuestion.topic_id)
        .where(AssessmentQuestion.assessment_id == assessment_id)
        .order_by(AssessmentQuestion.order_index)
    ).all()
    opt_rows = db.execute(
        select(AssessmentOption)
        .join(AssessmentQuestion, AssessmentQuestion.id == AssessmentOption.question_id)
        .where(AssessmentQuestion.assessment_id == assessment_id)
        .order_by(AssessmentOption.order_index)
    ).scalars().all()
    options_by_q: dict[int, list[OptionForStudent]] = defaultdict(list)
    for o in opt_rows:
        options_by_q[o.question_id].append(OptionForStudent(
            id=o.id, order_index=o.order_index, text=o.option_text,
        ))

    questions = [
        QuestionForStudent(
            id=q.id, order_index=q.order_index, topic=code,
            difficulty=q.difficulty, text=q.question_text, marks=q.marks,
            options=options_by_q[q.id],
        ) for q, code in q_rows
    ]
    return AssessmentForStudent(
        id=assessment.id, kind=assessment.kind, title=assessment.title,
        description=assessment.description, total_marks=assessment.total_marks,
        pass_ratio=float(assessment.pass_ratio),
        duration_minutes=assessment.duration_minutes, questions=questions,
    )


def submit_assessment(
    db: Session, user_id: int, assessment_id: int, req: AssessmentSubmitRequest,
) -> AttemptResult:
    assessment = db.get(Assessment, assessment_id)
    if assessment is None or not assessment.is_active:
        raise AssessmentError("Assessment not found")

    if assessment.kind == AssessmentKind.DIAGNOSTIC:
        profile = db.execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        ).scalar_one_or_none()
        if profile is None or profile.selected_level != assessment.target_level:
            raise AssessmentError("You cannot submit this diagnostic assessment")
    else:
        if assessment.section_id is None or not _has_section_access(db, user_id, assessment.section_id):
            raise AssessmentError("You cannot submit this assessment")

    q_rows = db.execute(
        select(AssessmentQuestion).where(AssessmentQuestion.assessment_id == assessment_id)
    ).scalars().all()
    if not q_rows:
        raise AssessmentError("Assessment has no questions")

    correct_by_q = dict(db.execute(
        select(AssessmentOption.question_id, AssessmentOption.id)
        .join(AssessmentQuestion, AssessmentQuestion.id == AssessmentOption.question_id)
        .where(
            AssessmentQuestion.assessment_id == assessment_id,
            AssessmentOption.is_correct.is_(True),
        )
    ).all())

    option_to_q = dict(db.execute(
        select(AssessmentOption.id, AssessmentOption.question_id)
        .join(AssessmentQuestion, AssessmentQuestion.id == AssessmentOption.question_id)
        .where(AssessmentQuestion.assessment_id == assessment_id)
    ).all())

    submitted = {a.question_id: a.option_id for a in req.answers}
    for qid, oid in submitted.items():
        if qid not in correct_by_q:
            raise AssessmentError(f"Question {qid} does not belong to this assessment")
        if option_to_q.get(oid) != qid:
            raise AssessmentError(f"Option {oid} does not belong to question {qid}")

    last_num = db.execute(
        select(func.max(AssessmentAttempt.attempt_number)).where(
            AssessmentAttempt.user_id == user_id,
            AssessmentAttempt.assessment_id == assessment_id,
        )
    ).scalar() or 0
    attempt_number = last_num + 1

    now = datetime.now(timezone.utc)
    attempt = AssessmentAttempt(
        user_id=user_id, assessment_id=assessment_id,
        attempt_number=attempt_number, status=AttemptStatus.SUBMITTED,
        submitted_at=now,
    )
    db.add(attempt)
    db.flush()

    topic_stats: dict[int, dict[str, float]] = defaultdict(
        lambda: {"questions_total": 0, "questions_correct": 0, "marks_total": 0.0, "marks_obtained": 0.0}
    )
    difficulty_stats: dict[Difficulty, dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0})
    question_results: list[QuestionResult] = []

    score_marks = 0.0
    total_marks = 0.0

    for q in q_rows:
        total_marks += q.marks
        selected = submitted.get(q.id)
        correct_id = correct_by_q[q.id]
        is_correct = selected == correct_id

        attempt.answers.append(type(attempt).answers.property.mapper.class_(  # AssessmentAnswer
            attempt_id=attempt.id, question_id=q.id,
            selected_option_id=selected, is_correct=is_correct, answered_at=now,
        ))

        if is_correct:
            score_marks += q.marks

        topic_stats[q.topic_id]["questions_total"] += 1
        topic_stats[q.topic_id]["marks_total"] += q.marks
        if is_correct:
            topic_stats[q.topic_id]["questions_correct"] += 1
            topic_stats[q.topic_id]["marks_obtained"] += q.marks

        difficulty_stats[q.difficulty]["total"] += 1
        if is_correct:
            difficulty_stats[q.difficulty]["correct"] += 1

        topic_code = db.get(Topic, q.topic_id).code
        question_results.append(QuestionResult(
            question_id=q.id, topic=topic_code, difficulty=q.difficulty,
            selected_option_id=selected, correct_option_id=correct_id,
            is_correct=is_correct, explanation=q.explanation,
        ))

    percentage = round((score_marks / total_marks) * 100, 2) if total_marks else 0.0
    passed = percentage >= float(assessment.pass_ratio) * 100

    attempt.score_marks = score_marks
    attempt.total_marks = total_marks
    attempt.percentage = percentage
    attempt.passed = passed

    for topic_id, s in topic_stats.items():
        accuracy = (s["questions_correct"] / s["questions_total"]) if s["questions_total"] else 0.0
        db.add(AttemptTopicResult(
            attempt_id=attempt.id, topic_id=topic_id,
            questions_total=int(s["questions_total"]),
            questions_correct=int(s["questions_correct"]),
            marks_total=s["marks_total"], marks_obtained=s["marks_obtained"],
            accuracy=round(accuracy, 4),
        ))

    db.flush()

    if assessment.kind == AssessmentKind.DIAGNOSTIC:
        recompute_skill_profile_from_attempt(db, user_id, attempt)
    else:
        section = db.get(LearningSection, assessment.section_id) if assessment.section_id else None
        if section is not None:
            evaluate_section(db, user_id, section)
        # Beginner students build their skill profile from section-ends
        recompute_skill_profile_from_attempt(db, user_id, attempt)

    # Auto-regenerate recommendations inside the same transaction.
    # Failure here rolls back the whole submission — no partial state.
    generate_recommendations(db, user_id)

    db.commit()
    db.refresh(attempt)

    topic_results = [
        TopicResult(
            topic=db.get(Topic, topic_id).code,
            questions_total=int(s["questions_total"]),
            questions_correct=int(s["questions_correct"]),
            accuracy=round(s["questions_correct"] / s["questions_total"], 4) if s["questions_total"] else 0.0,
        ) for topic_id, s in topic_stats.items()
    ]
    difficulty_results = [
        DifficultyResult(
            difficulty=d,
            questions_total=s["total"],
            questions_correct=s["correct"],
            accuracy=round(s["correct"] / s["total"], 4) if s["total"] else 0.0,
        ) for d, s in difficulty_stats.items()
    ]

    return AttemptResult(
        attempt_id=attempt.id, assessment_id=assessment.id,
        attempt_number=attempt.attempt_number, status=attempt.status,
        score_marks=float(attempt.score_marks), total_marks=float(attempt.total_marks),
        percentage=float(attempt.percentage), passed=bool(attempt.passed),
        submitted_at=attempt.submitted_at,
        topic_results=topic_results, difficulty_results=difficulty_results,
        question_results=question_results,
    )


def list_attempts(db: Session, user_id: int, assessment_id: int) -> list[AttemptHistoryItem]:
    rows = db.execute(
        select(AssessmentAttempt).where(
            AssessmentAttempt.user_id == user_id,
            AssessmentAttempt.assessment_id == assessment_id,
            AssessmentAttempt.status == AttemptStatus.SUBMITTED,
        ).order_by(AssessmentAttempt.submitted_at.desc())
    ).scalars().all()
    return [
        AttemptHistoryItem(
            attempt_id=a.id, attempt_number=a.attempt_number,
            score_marks=float(a.score_marks or 0), total_marks=float(a.total_marks or 0),
            percentage=float(a.percentage or 0), passed=bool(a.passed),
            submitted_at=a.submitted_at,
        ) for a in rows
    ]


def get_attempt_detail(db: Session, user_id: int, attempt_id: int) -> AttemptResult:
    attempt = db.get(AssessmentAttempt, attempt_id)
    if attempt is None or attempt.user_id != user_id:
        raise AssessmentError("Attempt not found")

    answers = attempt.answers
    selected_by_q = {a.question_id: a.selected_option_id for a in answers}
    correct_by_q = dict(db.execute(
        select(AssessmentOption.question_id, AssessmentOption.id)
        .join(AssessmentQuestion, AssessmentQuestion.id == AssessmentOption.question_id)
        .where(
            AssessmentQuestion.assessment_id == attempt.assessment_id,
            AssessmentOption.is_correct.is_(True),
        )
    ).all())

    q_rows = db.execute(
        select(AssessmentQuestion, Topic.code)
        .join(Topic, Topic.id == AssessmentQuestion.topic_id)
        .where(AssessmentQuestion.assessment_id == attempt.assessment_id)
        .order_by(AssessmentQuestion.order_index)
    ).all()

    question_results = [
        QuestionResult(
            question_id=q.id, topic=code, difficulty=q.difficulty,
            selected_option_id=selected_by_q.get(q.id),
            correct_option_id=correct_by_q[q.id],
            is_correct=selected_by_q.get(q.id) == correct_by_q[q.id],
            explanation=q.explanation,
        ) for q, code in q_rows
    ]

    topic_rows = db.execute(
        select(AttemptTopicResult, Topic.code)
        .join(Topic, Topic.id == AttemptTopicResult.topic_id)
        .where(AttemptTopicResult.attempt_id == attempt_id)
    ).all()
    topic_results = [
        TopicResult(topic=code, questions_total=r.questions_total,
                    questions_correct=r.questions_correct, accuracy=float(r.accuracy))
        for r, code in topic_rows
    ]

    difficulty_stats: dict[Difficulty, dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0})
    for q, _ in q_rows:
        difficulty_stats[q.difficulty]["total"] += 1
        if selected_by_q.get(q.id) == correct_by_q[q.id]:
            difficulty_stats[q.difficulty]["correct"] += 1
    difficulty_results = [
        DifficultyResult(difficulty=d, questions_total=s["total"],
                         questions_correct=s["correct"],
                         accuracy=round(s["correct"] / s["total"], 4) if s["total"] else 0.0)
        for d, s in difficulty_stats.items()
    ]

    return AttemptResult(
        attempt_id=attempt.id, assessment_id=attempt.assessment_id,
        attempt_number=attempt.attempt_number, status=attempt.status,
        score_marks=float(attempt.score_marks or 0), total_marks=float(attempt.total_marks or 0),
        percentage=float(attempt.percentage or 0), passed=bool(attempt.passed),
        submitted_at=attempt.submitted_at,
        topic_results=topic_results, difficulty_results=difficulty_results,
        question_results=question_results,
    )