def _register_payload(email: str = "a@example.com") -> dict:
    return {
        "full_name": "Alice Student",
        "email": email,
        "course": "B.Tech CSE",
        "academic_year": 3,
        "password": "Passw0rd1",
        "confirm_password": "Passw0rd1",
    }


def test_register_and_login(client):
    r = client.post("/api/v1/auth/register", json=_register_payload())
    assert r.status_code == 201, r.text
    assert r.json()["email"] == "a@example.com"

    r = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "Passw0rd1"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert token

    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["full_name"] == "Alice Student"


def test_duplicate_email_rejected(client):
    client.post("/api/v1/auth/register", json=_register_payload())
    r = client.post("/api/v1/auth/register", json=_register_payload())
    assert r.status_code == 409


def test_wrong_password_rejected(client):
    client.post("/api/v1/auth/register", json=_register_payload())
    r = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "wrongpass1"})
    assert r.status_code == 401


def test_protected_route_requires_token(client):
    r = client.get("/api/v1/profile")
    assert r.status_code == 401


def test_passwords_must_match():
    from pydantic import ValidationError
    from app.schemas.auth import RegisterRequest
    import pytest
    with pytest.raises(ValidationError):
        RegisterRequest(
            full_name="A", email="x@y.com", course="CSE", academic_year=2,
            password="Passw0rd1", confirm_password="Different1",
        )