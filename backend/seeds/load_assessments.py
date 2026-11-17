"""Seed and validate assessment question banks.

Usage:
    python -m backend.seeds.load_assessments --dir backend/seeds --replace
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import (
    Assessment, AssessmentOption, AssessmentQuestion,
    LearningSection, Topic,
)
from app.models.enums import (
    AssessmentKind, Difficulty, StudentLevel,
)

SEED_FILES = [
    "intermediate_diagnostic.json",
    "advanced_diagnostic.json",
    "fundamentals_end.json",
    "arrays_end.json",
    "strings_end.json",
]


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
class ValidationError(Exception):
    pass


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValidationError(msg)


def validate_document(doc: dict[str, Any], known_topics: dict[str, int]) -> None:
    _require("assessment" in doc, "missing 'assessment' block")
    _require("questions" in doc, "missing 'questions' list")
    a = doc["assessment"]

    _require(a["kind"] in {"DIAGNOSTIC", "SECTION_END"}, "invalid assessment.kind")
    if a["kind"] == "DIAGNOSTIC":
        _require(
            a.get("target_level") in {"INTERMEDIATE", "ADVANCED"},
            "diagnostic must target INTERMEDIATE or ADVANCED",
        )
    else:
        _require("section_slug" in a, "SECTION_END requires 'section_slug'")

    # Per-question shape
    seen_texts: set[str] = set()
    for i, q in enumerate(doc["questions"], start=1):
        _require(q.get("order") == i, f"question order must be sequential (got {q.get('order')} at position {i})")
        _require(q["topic"] in known_topics, f"q{i}: unknown topic {q['topic']!r}")
        _require(q["difficulty"] in {"EASY", "MEDIUM", "HARD"}, f"q{i}: bad difficulty")
        _require(isinstance(q["marks"], int) and q["marks"] > 0, f"q{i}: marks must be positive int")
        _require(isinstance(q["text"], str) and q["text"].strip(), f"q{i}: empty text")
        opts = q["options"]
        _require(isinstance(opts, list) and len(opts) == 4, f"q{i}: must have exactly 4 options")
        _require(all(isinstance(o, str) and o.strip() for o in opts), f"q{i}: empty option")
        _require(len(set(opts)) == 4, f"q{i}: duplicate options")
        _require(isinstance(q["correct_index"], int) and 0 <= q["correct_index"] <= 3,
                 f"q{i}: correct_index must be in [0,3]")
        _require(isinstance(q["explanation"], str) and q["explanation"].strip(),
                 f"q{i}: explanation required (used at grading time)")
        _require(q["text"] not in seen_texts, f"q{i}: duplicate question text")
        seen_texts.add(q["text"])

    # Distribution asserts
    dist = doc.get("distribution", {})
    by_topic = {}
    by_diff = {"EASY": 0, "MEDIUM": 0, "HARD": 0}
    for q in doc["questions"]:
        by_topic[q["topic"]] = by_topic.get(q["topic"], 0) + 1
        by_diff[q["difficulty"]] += 1

    for topic, expected in dist.get("by_topic", {}).items():
        _require(by_topic.get(topic, 0) == expected,
                 f"topic count mismatch for {topic}: got {by_topic.get(topic, 0)}, expected {expected}")
    for diff, expected in dist.get("by_difficulty", {}).items():
        _require(by_diff[diff] == expected,
                 f"difficulty count mismatch for {diff}: got {by_diff[diff]}, expected {expected}")

    # Total marks
    total = sum(q["marks"] for q in doc["questions"])
    _require(total == a["total_marks"],
             f"total_marks mismatch: questions sum to {total}, assessment declares {a['total_marks']}")


# --------------------------------------------------------------------------
# Insertion
# --------------------------------------------------------------------------
def _upsert_assessment(db: Session, doc: dict[str, Any]) -> Assessment:
    a = doc["assessment"]
    kind = AssessmentKind(a["kind"])

    stmt = select(Assessment).where(Assessment.kind == kind)
    if kind is AssessmentKind.DIAGNOSTIC:
        stmt = stmt.where(Assessment.target_level == StudentLevel(a["target_level"]))
    else:
        section = db.execute(
            select(LearningSection).where(LearningSection.slug == a["section_slug"])
        ).scalar_one_or_none()
        _require(section is not None, f"section slug not found: {a['section_slug']}")
        stmt = stmt.where(Assessment.section_id == section.id)

    existing = db.execute(stmt).scalar_one_or_none()
    if existing is not None:
        return existing

    if kind is AssessmentKind.DIAGNOSTIC:
        assessment = Assessment(
            kind=kind,
            target_level=StudentLevel(a["target_level"]),
            title=a["title"],
            description=a.get("description"),
            total_marks=a["total_marks"],
            pass_ratio=a["pass_ratio"],
            duration_minutes=a.get("duration_minutes"),
        )
    else:
        assessment = Assessment(
            kind=kind,
            section_id=section.id,
            title=a["title"],
            description=a.get("description"),
            total_marks=a["total_marks"],
            pass_ratio=a["pass_ratio"],
            duration_minutes=a.get("duration_minutes"),
        )
    db.add(assessment)
    db.flush()
    return assessment


def _insert_questions(
    db: Session, assessment: Assessment, doc: dict[str, Any], topic_ids: dict[str, int]
) -> None:
    for q in doc["questions"]:
        question = AssessmentQuestion(
            assessment_id=assessment.id,
            topic_id=topic_ids[q["topic"]],
            difficulty=Difficulty(q["difficulty"]),
            question_text=q["text"],
            explanation=q["explanation"],
            marks=q["marks"],
            order_index=q["order"],
        )
        db.add(question)
        db.flush()
        for idx, text in enumerate(q["options"]):
            db.add(
                AssessmentOption(
                    question_id=question.id,
                    option_text=text,
                    is_correct=(idx == q["correct_index"]),
                    order_index=idx,
                )
            )


def _clear_questions(db: Session, assessment: Assessment) -> None:
    db.execute(
        delete(AssessmentQuestion).where(AssessmentQuestion.assessment_id == assessment.id)
    )


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def load_file(
    db: Session,
    path: Path,
    topic_ids: dict[str, int],
    replace: bool,
) -> tuple[str, int, str]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    validate_document(doc, topic_ids)
    assessment = _upsert_assessment(db, doc)
    if replace:
        _clear_questions(db, assessment)
    existing = db.scalar(
        select(func.count()).select_from(AssessmentQuestion)
        .where(AssessmentQuestion.assessment_id == assessment.id)
    )
    _require(existing == 0, f"{path.name}: assessment already has {existing} questions (use --replace)")
    _insert_questions(db, assessment, doc, topic_ids)
    return (assessment.kind.value, len(doc["questions"]), assessment.title)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="backend/seeds")
    ap.add_argument("--replace", action="store_true")
    args = ap.parse_args()

    with SessionLocal() as db:
        topic_ids = dict(db.execute(select(Topic.code, Topic.id)).all())
        failures: list[str] = []

        for name in SEED_FILES:
            path = Path(args.dir) / name
            try:
                kind, n, title = load_file(db, path, topic_ids, args.replace)
                db.commit()
                print(f"OK  {name:32s}  {kind:12s}  {n:>2d} questions  -> {title}")
            except ValidationError as exc:
                db.rollback()
                failures.append(f"{name}: {exc}")
                print(f"FAIL {name}: {exc}", file=sys.stderr)

        if failures:
            print(f"\n{len(failures)} file(s) failed; no changes committed for them.", file=sys.stderr)
            return 1
        return 0


if __name__ == "__main__":
    sys.exit(main())