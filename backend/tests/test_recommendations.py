"""Tests for the recommendation engine (Deliverable D)."""
from __future__ import annotations

from sqlalchemy import select

from app.models import Recommendation, User
from app.models.enums import RecommendationStatus


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------

def test_weak_topic_relevance():
    from ml_engine.recommendation.rule_based import weak_topic_relevance
    assert weak_topic_relevance(0.0) == 1.0
    assert weak_topic_relevance(0.4) == 0.6
    assert weak_topic_relevance(1.0) == 0.0
    assert weak_topic_relevance(-0.1) == 1.0   # clamped
    assert weak_topic_relevance(1.5) == 0.0    # clamped


def test_difficulty_suitability():
    from ml_engine.recommendation.rule_based import difficulty_suitability
    # Exact match → 1.0
    assert difficulty_suitability(0, 0) == 1.0
    assert difficulty_suitability(1, 1) == 1.0
    assert difficulty_suitability(2, 2) == 1.0
    # 1-level off → 0.5
    assert difficulty_suitability(0, 1) == 0.5
    assert difficulty_suitability(2, 1) == 0.5
    # 2-level off → 0.0
    assert difficulty_suitability(0, 2) == 0.0
    assert difficulty_suitability(2, 0) == 0.0


def test_prerequisite_readiness():
    from ml_engine.recommendation.rule_based import prerequisite_readiness
    assert prerequisite_readiness(0, 0) == 1.0
    assert prerequisite_readiness(0, 2) == 0.0
    assert prerequisite_readiness(1, 2) == 0.5
    assert prerequisite_readiness(2, 2) == 1.0


def test_recommendation_score_weights():
    from ml_engine.recommendation.rule_based import recommendation_score
    assert abs(recommendation_score(1, 1, 1) - 1.0) < 1e-9
    assert recommendation_score(0, 0, 0) == 0.0
    # Weights: W=0.40, D=0.35, P=0.25
    assert abs(recommendation_score(1, 0, 0) - 0.40) < 1e-9
    assert abs(recommendation_score(0, 1, 0) - 0.35) < 1e-9
    assert abs(recommendation_score(0, 0, 1) - 0.25) < 1e-9
    assert abs(recommendation_score(0.5, 0.5, 0.5) - 0.50) < 1e-9


def test_classify_topic_thresholds():
    from ml_engine.recommendation.rule_based import classify_topic
    from app.models.enums import SkillTopicClassification as C
    assert classify_topic(0.0) == C.WEAK
    assert classify_topic(0.399) == C.WEAK
    assert classify_topic(0.40) == C.NEEDS_REVISION
    assert classify_topic(0.699) == C.NEEDS_REVISION
    assert classify_topic(0.70) == C.STRONG
    assert classify_topic(1.0) == C.STRONG


def test_target_difficulty_for():
    from ml_engine.recommendation.rule_based import target_difficulty_for
    from app.models.enums import Difficulty
    assert target_difficulty_for(0.0) == Difficulty.EASY
    assert target_difficulty_for(0.39) == Difficulty.EASY
    assert target_difficulty_for(0.40) == Difficulty.MEDIUM
    assert target_difficulty_for(0.69) == Difficulty.MEDIUM
    assert target_difficulty_for(0.70) == Difficulty.HARD


def test_ranking_top_n_and_dedupe():
    from ml_engine.recommendation.ranking import rank_top_n
    items = [
        {"id": 1, "score": 0.8},
        {"id": 2, "score": 0.9},
        {"id": 3, "score": 0.7},
        {"id": 1, "score": 0.85},   # dupe id=1, higher score
        {"id": 4, "score": 0.6},
    ]
    ranked = rank_top_n(items, key_fn=lambda c: c["id"], score_fn=lambda c: c["score"], limit=3)
    assert len(ranked) == 3
    assert ranked[0]["id"] == 2      # 0.9
    assert ranked[1]["id"] == 1      # 0.85 (best for id=1)
    assert ranked[2]["id"] == 3      # 0.7


# ---------------------------------------------------------------------------
# End-to-end tests (use the conftest fixtures)
# ---------------------------------------------------------------------------

def _register(client, email: str, level: str) -> str:
    client.post("/api/v1/auth/register", json={
        "full_name": "Rec User", "email": email, "course": "CSE",
        "academic_year": 3, "password": "Passw0rd1", "confirm_password": "Passw0rd1",
    })
    token = client.post("/api/v1/auth/login",
                        json={"email": email, "password": "Passw0rd1"}).json()["access_token"]
    r = client.post("/api/v1/onboarding",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"preferred_language": "PYTHON", "selected_level": level})
    assert r.status_code == 200, r.text
    return token


def _user_id(db, email: str) -> int:
    return db.execute(select(User).where(User.email == email)).scalar_one().id


def _active_recs(db, user_id: int) -> list[Recommendation]:
    return list(db.execute(
        select(Recommendation).where(
            Recommendation.user_id == user_id,
            Recommendation.status == RecommendationStatus.ACTIVE,
        )
    ).scalars().all())


def test_no_recommendations_without_skill_profile(client, db):
    token = _register(client, "nosp@example.com", "BEGINNER")
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/api/v1/recommendations/refresh", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["engine_available"] is True
    assert body["items"] == []
    assert _active_recs(db, _user_id(db, "nosp@example.com")) == []


def test_weak_arrays_from_diagnostic_yields_locked_preview(client, db):
    token = _register(client, "diag@example.com", "INTERMEDIATE")
    h = {"Authorization": f"Bearer {token}"}

    diag = next(a for a in client.get("/api/v1/assessments", headers=h).json()
                if a["kind"] == "DIAGNOSTIC")
    qs = client.get(f"/api/v1/assessments/{diag['id']}", headers=h).json()["questions"]
    wrong = [{"question_id": q["id"], "option_id": q["options"][1]["id"]} for q in qs]
    r = client.post(f"/api/v1/assessments/{diag['id']}/submit",
                    json={"answers": wrong}, headers=h)
    assert r.status_code == 200, r.text

    r = client.get("/api/v1/recommendations", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["engine_available"] is True
    items = body["items"]
    # Arrays section is locked (student is not enrolled in the beginner roadmap)
    assert all(i["kind"] == "LOCKED_PREVIEW" for i in items), items
    # At least one section-level hint and at least one item preview
    assert any(i["item_id"] is None and i["section_id"] is not None for i in items)
    assert any(i["item_id"] is not None for i in items)
    # No actionable and no revision
    assert not any(i["kind"] == "ACTIONABLE" for i in items)
    # No duplicates per item
    item_ids = [i["item_id"] for i in items if i["item_id"] is not None]
    assert len(item_ids) == len(set(item_ids))
    # Reason strings non-empty
    for i in items:
        assert i["reason"]


def test_failed_assessment_yields_revision_recommendations(client, db):
    token = _register(client, "rev@example.com", "BEGINNER")
    h = {"Authorization": f"Bearer {token}"}

    # Complete both Fundamentals lessons
    fund = next(s for s in client.get("/api/v1/sections", headers=h).json()["sections"]
                if s["slug"] == "fundamentals")
    detail = client.get(f"/api/v1/sections/{fund['id']}", headers=h).json()
    for item in detail["items"]:
        r = client.patch(f"/api/v1/progress/{item['id']}",
                         json={"is_completed": True}, headers=h)
        assert r.status_code == 200

    # Fundamentals section-end has 2 questions. Answer one correctly, one wrong → 50%.
    assess = next(a for a in client.get("/api/v1/assessments", headers=h).json()
                  if a["section_id"] == fund["id"])
    qs = client.get(f"/api/v1/assessments/{assess['id']}", headers=h).json()["questions"]
    # First answer correctly (option 0 is 'A' and both Fund questions have correct 'A' or 'B';
    # use revealed answers from a probe submission)
    probe = [{"question_id": q["id"], "option_id": q["options"][0]["id"]} for q in qs]
    probe_result = client.post(f"/api/v1/assessments/{assess['id']}/submit",
                               json={"answers": probe}, headers=h).json()
    correct_ids = {qr["question_id"]: qr["correct_option_id"]
                   for qr in probe_result["question_results"]}
    # Submit one correct + one wrong → 50%
    q1, q2 = qs[0], qs[1]
    mixed = [
        {"question_id": q1["id"], "option_id": correct_ids[q1["id"]]},
        {"question_id": q2["id"], "option_id": correct_ids[q2["id"]]},
    ]
    # Actually 2/2 is 100%. To force 50%, take only 1 correct:
    only_one = [
        {"question_id": q1["id"], "option_id": correct_ids[q1["id"]]},
        {"question_id": q2["id"], "option_id": [o["id"] for o in q2["options"]
                                                if o["id"] != correct_ids[q2["id"]]][0]},
    ]
    r = client.post(f"/api/v1/assessments/{assess['id']}/submit",
                    json={"answers": only_one}, headers=h)
    assert r.status_code == 200
    assert r.json()["percentage"] == 50.0

    # Recommendations: completed Fundamentals items, topic NEEDS_REVISION → REVISION
    recs = client.get("/api/v1/recommendations", headers=h).json()["items"]
    assert any(r["kind"] == "REVISION" for r in recs), recs
    for r in recs:
        assert r["reason"]


def test_generation_is_idempotent(client, db):
    token = _register(client, "idem@example.com", "INTERMEDIATE")
    h = {"Authorization": f"Bearer {token}"}
    diag = next(a for a in client.get("/api/v1/assessments", headers=h).json()
                if a["kind"] == "DIAGNOSTIC")
    qs = client.get(f"/api/v1/assessments/{diag['id']}", headers=h).json()["questions"]
    wrong = [{"question_id": q["id"], "option_id": q["options"][1]["id"]} for q in qs]
    client.post(f"/api/v1/assessments/{diag['id']}/submit",
                json={"answers": wrong}, headers=h)

    r1 = client.get("/api/v1/recommendations", headers=h).json()["items"]
    r2 = client.post("/api/v1/recommendations/refresh", headers=h).json()["items"]

    def sig(items):
        return sorted(
            (i["kind"], i["item_id"] or 0, i["section_id"] or 0, round(i["score"], 4))
            for i in items
        )
    assert sig(r1) == sig(r2)


def test_no_duplicate_active_recommendations(client, db):
    token = _register(client, "dup@example.com", "INTERMEDIATE")
    h = {"Authorization": f"Bearer {token}"}
    diag = next(a for a in client.get("/api/v1/assessments", headers=h).json()
                if a["kind"] == "DIAGNOSTIC")
    qs = client.get(f"/api/v1/assessments/{diag['id']}", headers=h).json()["questions"]
    wrong = [{"question_id": q["id"], "option_id": q["options"][1]["id"]} for q in qs]
    client.post(f"/api/v1/assessments/{diag['id']}/submit",
                json={"answers": wrong}, headers=h)
    client.post("/api/v1/recommendations/refresh", headers=h)

    user_id = _user_id(db, "dup@example.com")
    actives = _active_recs(db, user_id)
    item_ids = [r.item_id for r in actives if r.item_id is not None]
    assert len(item_ids) == len(set(item_ids)), item_ids