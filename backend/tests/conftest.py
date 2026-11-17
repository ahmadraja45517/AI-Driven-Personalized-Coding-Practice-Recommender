from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import (
    Assessment, AssessmentOption, AssessmentQuestion,
    Base, LearningItem, LearningSection, SectionItem, Topic,
)
from app.models.enums import (
    AssessmentKind, ContentSource, Difficulty, LearningItemKind,
    SectionContentStatus, StudentLevel,
)


def _strip_partial_indexes(metadata) -> None:
    """SQLite cannot express postgresql_where partial indexes; strip them
    before create_all so tests don't accidentally create plain unique
    indexes on columns meant to be conditional."""
    for table in metadata.tables.values():
        for idx in list(table.indexes):
            pg = idx.dialect_options.get("postgresql", {}) if hasattr(idx, "dialect_options") else {}
            if pg.get("where") is not None:
                table.indexes.discard(idx)

def _patch_biginteger_for_sqlite(metadata) -> None:
    """SQLite only auto-increments INTEGER PRIMARY KEY, not BIGINT PRIMARY KEY.
    Rewrite every BigInteger column to Integer so autoincrement works in tests.
    The production Postgres schema (via Alembic) keeps BigInteger -> BIGSERIAL."""
    from sqlalchemy import BigInteger, Integer
    for table in metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, BigInteger):
                col.type = Integer()

@pytest.fixture()
def db() -> Generator[Session, None, None]:
    _strip_partial_indexes(Base.metadata)
    _patch_biginteger_for_sqlite(Base.metadata)      # <-- new line
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = TestSession()
    _seed(session)
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _seed(db: Session) -> None:
    fundamentals = Topic(
        code="fundamentals", name="Fundamentals",
        is_diagnostic_topic=False, order_index=1, is_active=True,
    )
    arrays = Topic(
        code="arrays", name="Arrays",
        is_diagnostic_topic=True, order_index=2, is_active=True,
    )
    db.add_all([fundamentals, arrays])
    db.flush()
    fund_sec = LearningSection(
        slug="fundamentals", title="Fundamentals", topic_id=fundamentals.id,
        target_level=StudentLevel.BEGINNER, order_index=1,
        content_status=SectionContentStatus.PUBLISHED,
    )
    arr_sec = LearningSection(
        slug="arrays", title="Arrays", topic_id=arrays.id,
        target_level=StudentLevel.BEGINNER, order_index=2,
        content_status=SectionContentStatus.PUBLISHED,
    )
    db.add_all([fund_sec, arr_sec])
    db.flush()

    f1 = LearningItem(topic_id=fundamentals.id, kind=LearningItemKind.LESSON,
                      source=ContentSource.INTERNAL, title="Lesson 1",
                      content_md="# L1", is_active=True)
    f2 = LearningItem(topic_id=fundamentals.id, kind=LearningItemKind.LESSON,
                      source=ContentSource.INTERNAL, title="Lesson 2",
                      content_md="# L2", is_active=True)
    db.add_all([f1, f2])
    db.flush()
    db.add_all([
        SectionItem(section_id=fund_sec.id, item_id=f1.id, order_index=1, is_required=True),
        SectionItem(section_id=fund_sec.id, item_id=f2.id, order_index=2, is_required=True),
    ])

    a1 = LearningItem(topic_id=arrays.id, kind=LearningItemKind.EXTERNAL_PROBLEM,
                      source=ContentSource.LEETCODE, title="Two Sum",
                      external_url="https://leetcode.com/problems/two-sum/",
                      difficulty=Difficulty.EASY, is_active=True)
    a2 = LearningItem(topic_id=arrays.id, kind=LearningItemKind.EXTERNAL_PROBLEM,
                      source=ContentSource.LEETCODE, title="Max Subarray",
                      external_url="https://leetcode.com/problems/maximum-subarray/",
                      difficulty=Difficulty.MEDIUM, is_active=True)
    db.add_all([a1, a2])
    db.flush()
    db.add_all([
        SectionItem(section_id=arr_sec.id, item_id=a1.id, order_index=1, is_required=True),
        SectionItem(section_id=arr_sec.id, item_id=a2.id, order_index=2, is_required=True),
    ])

    _add_assessment(db, AssessmentKind.SECTION_END, fund_sec.id, None, "Fundamentals End",
                    [(fundamentals.id, Difficulty.EASY, "Fund Q1", "A", ["A", "B", "C", "D"]),
                     (fundamentals.id, Difficulty.MEDIUM, "Fund Q2", "B", ["A", "B", "C", "D"])])
    _add_assessment(db, AssessmentKind.SECTION_END, arr_sec.id, None, "Arrays End",
                    [(arrays.id, Difficulty.EASY, "Arr Q1", "A", ["A", "B", "C", "D"]),
                     (arrays.id, Difficulty.HARD, "Arr Q2", "D", ["A", "B", "C", "D"])])
    _add_assessment(db, AssessmentKind.DIAGNOSTIC, None, StudentLevel.INTERMEDIATE,
                    "Intermediate Diagnostic",
                    [(arrays.id, Difficulty.EASY, "Int Q1", "A", ["A", "B", "C", "D"]),
                     (arrays.id, Difficulty.MEDIUM, "Int Q2", "B", ["A", "B", "C", "D"]),
                     (arrays.id, Difficulty.HARD, "Int Q3", "C", ["A", "B", "C", "D"])])
    _add_assessment(db, AssessmentKind.DIAGNOSTIC, None, StudentLevel.ADVANCED,
                    "Advanced Diagnostic",
                    [(arrays.id, Difficulty.MEDIUM, "Adv Q1", "A", ["A", "B", "C", "D"]),
                     (arrays.id, Difficulty.HARD,   "Adv Q2", "B", ["A", "B", "C", "D"]),
                     (arrays.id, Difficulty.HARD,   "Adv Q3", "C", ["A", "B", "C", "D"])])

def _add_assessment(db, kind, section_id, target_level, title, questions) -> None:
    a = Assessment(
        kind=kind, section_id=section_id, target_level=target_level, title=title,
        total_marks=len(questions), pass_ratio=0.7,
        is_active=True,          # <-- explicit so SQLite stores 1, not 'true'
    )
    db.add(a)
    db.flush()
    for i, (topic_id, diff, text, correct, opts) in enumerate(questions, start=1):
        q = AssessmentQuestion(
            assessment_id=a.id, topic_id=topic_id, difficulty=diff,
            question_text=text, explanation=f"Explanation for {text}",
            marks=1, order_index=i,
        )
        db.add(q)
        db.flush()
        for idx, opt in enumerate(opts):
            db.add(AssessmentOption(
                question_id=q.id, option_text=opt,
                is_correct=(opt == correct), order_index=idx,
            ))