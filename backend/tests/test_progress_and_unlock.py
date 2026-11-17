def _beginner_token(client) -> str:
    client.post("/api/v1/auth/register", json={
        "full_name": "Bea", "email": "be@example.com", "course": "CSE",
        "academic_year": 2, "password": "Passw0rd1", "confirm_password": "Passw0rd1",
    })
    token = client.post("/api/v1/auth/login",
                        json={"email": "be@example.com", "password": "Passw0rd1"}).json()["access_token"]
    client.post("/api/v1/onboarding",
                headers={"Authorization": f"Bearer {token}"},
                json={"preferred_language": "JAVA", "selected_level": "BEGINNER"})
    return token


def test_first_section_unlocked_and_rest_locked(client):
    token = _beginner_token(client)
    h = {"Authorization": f"Bearer {token}"}
    data = client.get("/api/v1/sections", headers=h).json()
    assert data["enrolled"] is True
    fund = next(s for s in data["sections"] if s["slug"] == "fundamentals")
    arr = next(s for s in data["sections"] if s["slug"] == "arrays")
    assert fund["status"] == "UNLOCKED"
    assert arr["status"] == "LOCKED"


def test_progress_updates_require_accessible_section(client):
    token = _beginner_token(client)
    h = {"Authorization": f"Bearer {token}"}
    data = client.get("/api/v1/sections", headers=h).json()
    arr = next(s for s in data["sections"] if s["slug"] == "arrays")
    detail = client.get(f"/api/v1/sections/{arr['id']}", headers=h)
    assert detail.status_code == 403


def test_unlock_requires_both_completion_and_assessment(client):
    token = _beginner_token(client)
    h = {"Authorization": f"Bearer {token}"}
    fund = next(s for s in client.get("/api/v1/sections", headers=h).json()["sections"]
                if s["slug"] == "fundamentals")
    detail = client.get(f"/api/v1/sections/{fund['id']}", headers=h).json()
    item_ids = [i["id"] for i in detail["items"]]

    # Mark both lessons complete -> 100% completion, no assessment yet
    for iid in item_ids:
        r = client.patch(f"/api/v1/progress/{iid}", json={"is_completed": True}, headers=h)
        assert r.status_code == 200, r.text

    arr = next(s for s in client.get("/api/v1/sections", headers=h).json()["sections"]
               if s["slug"] == "arrays")
    assert arr["status"] == "LOCKED", "completion alone must not unlock arrays"

    # Take fundamentals end assessment, submit wrong on purpose
    assessments = client.get("/api/v1/assessments", headers=h).json()
    fund_assess = next(a for a in assessments if a["section_id"] == fund["id"])
    qs = client.get(f"/api/v1/assessments/{fund_assess['id']}", headers=h).json()["questions"]
    wrong = [{"question_id": q["id"], "option_id": q["options"][1]["id"]} for q in qs]
    client.post(f"/api/v1/assessments/{fund_assess['id']}/submit", json={"answers": wrong}, headers=h)

    arr = next(s for s in client.get("/api/v1/sections", headers=h).json()["sections"]
               if s["slug"] == "arrays")
    assert arr["status"] == "LOCKED", "failing the assessment must not unlock arrays"

    # Submit the correct answers -> unlock
    correct_ids = {}
    # first submission already revealed correct answers in the response
    r = client.post(f"/api/v1/assessments/{fund_assess['id']}/submit", json={"answers": wrong}, headers=h).json()
    for qr in r["question_results"]:
        correct_ids[qr["question_id"]] = qr["correct_option_id"]
    right = [{"question_id": qid, "option_id": oid} for qid, oid in correct_ids.items()]
    client.post(f"/api/v1/assessments/{fund_assess['id']}/submit", json={"answers": right}, headers=h)

    arr = next(s for s in client.get("/api/v1/sections", headers=h).json()["sections"]
               if s["slug"] == "arrays")
    assert arr["status"] == "UNLOCKED"
    fund_after = next(s for s in client.get("/api/v1/sections", headers=h).json()["sections"]
                      if s["slug"] == "fundamentals")
    assert fund_after["status"] == "COMPLETED"


def test_level_recommendation_does_not_change_selected_level(client):
    client.post("/api/v1/auth/register", json={
        "full_name": "Zed", "email": "z@example.com", "course": "CSE",
        "academic_year": 3, "password": "Passw0rd1", "confirm_password": "Passw0rd1",
    })
    token = client.post("/api/v1/auth/login",
                        json={"email": "z@example.com", "password": "Passw0rd1"}).json()["access_token"]
    client.post("/api/v1/onboarding",
                headers={"Authorization": f"Bearer {token}"},
                json={"preferred_language": "CPP", "selected_level": "ADVANCED"})   
    h = {"Authorization": f"Bearer {token}"}

    diag = next(a for a in client.get("/api/v1/assessments", headers=h).json()
                if a["kind"] == "DIAGNOSTIC")
    qs = client.get(f"/api/v1/assessments/{diag['id']}", headers=h).json()["questions"]
    wrong = [{"question_id": q["id"], "option_id": q["options"][1]["id"]} for q in qs]
    client.post(f"/api/v1/assessments/{diag['id']}/submit", json={"answers": wrong}, headers=h)

    profile = client.get("/api/v1/profile", headers=h).json()
    assert profile["selected_level"] == "ADVANCED"  # unchanged
    # With all-wrong answers, demonstrated level should be BEGINNER
    assert profile["demonstrated_level"] == "BEGINNER"
    assert profile["level_recommendation"]["show"] is True
    assert profile["level_recommendation"]["recommended_level"] == "BEGINNER"