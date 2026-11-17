def _make_user(client, level: str = "INTERMEDIATE") -> str:
    client.post("/api/v1/auth/register", json={
        "full_name": "Bob", "email": "b@example.com", "course": "CSE",
        "academic_year": 3, "password": "Passw0rd1", "confirm_password": "Passw0rd1",
    })
    r = client.post("/api/v1/auth/login", json={"email": "b@example.com", "password": "Passw0rd1"})
    token = r.json()["access_token"]
    client.post(
        "/api/v1/onboarding",
        headers={"Authorization": f"Bearer {token}"},
        json={"preferred_language": "PYTHON", "selected_level": level},
    )
    return token


def test_question_payload_never_includes_answers(client):
    token = _make_user(client)
    r = client.get("/api/v1/assessments", headers={"Authorization": f"Bearer {token}"})
    diagnostic_id = next(a["id"] for a in r.json() if a["kind"] == "DIAGNOSTIC")
    r = client.get(f"/api/v1/assessments/{diagnostic_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    for q in r.json()["questions"]:
        assert "explanation" not in q
        for opt in q["options"]:
            assert "is_correct" not in opt


def test_submission_scores_and_reveals(client):
    token = _make_user(client)
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/assessments", headers=h)
    diag = next(a for a in r.json() if a["kind"] == "DIAGNOSTIC")
    r = client.get(f"/api/v1/assessments/{diag['id']}", headers=h)
    qs = r.json()["questions"]

    # Find correct option IDs by trial: submit all "A" first, then adjust.
    # Simpler: read the correct option from the grader via a first submission.
    answers = [{"question_id": q["id"], "option_id": q["options"][0]["id"]} for q in qs]
    r = client.post(f"/api/v1/assessments/{diag['id']}/submit", json={"answers": answers}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["attempt_number"] == 1
    assert "question_results" in body
    for qr in body["question_results"]:
        assert "explanation" in qr
        assert "correct_option_id" in qr


def test_retakes_and_best_attempt_used(client):
    token = _make_user(client)
    h = {"Authorization": f"Bearer {token}"}
    diag = next(a for a in client.get("/api/v1/assessments", headers=h).json()
                if a["kind"] == "DIAGNOSTIC")
    qs = client.get(f"/api/v1/assessments/{diag['id']}", headers=h).json()["questions"]

    # First attempt: all wrong
    wrong = [{"question_id": q["id"], "option_id": q["options"][1]["id"]} for q in qs]
    r1 = client.post(f"/api/v1/assessments/{diag['id']}/submit", json={"answers": wrong}, headers=h).json()

    # Get correct answers from attempt result
    correct_ids = {qr["question_id"]: qr["correct_option_id"] for qr in r1["question_results"]}
    right = [{"question_id": qid, "option_id": oid} for qid, oid in correct_ids.items()]
    r2 = client.post(f"/api/v1/assessments/{diag['id']}/submit", json={"answers": right}, headers=h).json()

    assert r2["attempt_number"] == 2
    assert r2["percentage"] > r1["percentage"]

    history = client.get(f"/api/v1/assessments/{diag['id']}/attempts", headers=h).json()
    assert len(history) == 2
    assert any(a["percentage"] == 100.0 for a in history)


def test_best_attempt_preserved_as_first_latest_best(client):
    token = _make_user(client)
    h = {"Authorization": f"Bearer {token}"}
    diag = next(a for a in client.get("/api/v1/assessments", headers=h).json()
                if a["kind"] == "DIAGNOSTIC")
    qs = client.get(f"/api/v1/assessments/{diag['id']}", headers=h).json()["questions"]

    r1 = client.post(f"/api/v1/assessments/{diag['id']}/submit",
                     json={"answers": [{"question_id": q["id"], "option_id": q["options"][0]["id"]} for q in qs]},
                     headers=h).json()
    correct_ids = {qr["question_id"]: qr["correct_option_id"] for qr in r1["question_results"]}
    right = [{"question_id": qid, "option_id": oid} for qid, oid in correct_ids.items()]
    client.post(f"/api/v1/assessments/{diag['id']}/submit", json={"answers": right}, headers=h)

    dash = client.get("/api/v1/dashboard", headers=h).json()
    hist = dash["diagnostic_history"]
    assert hist["attempts_count"] == 2
    assert hist["first_pct"] == r1["percentage"]
    assert hist["latest_pct"] == 100.0
    assert hist["best_pct"] == 100.0