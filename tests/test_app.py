import pytest
from werkzeug.security import generate_password_hash

import app as dashboard_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_app, "AUTH_DB", tmp_path / "test-auth.db")
    dashboard_app.init_auth_db()
    dashboard_app.app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SECRET_KEY="test-secret-key",
    )
    with dashboard_app.app.test_client() as test_client:
        yield test_client


def create_user(username="manager", password="correct-horse-battery-staple"):
    with dashboard_app.get_auth_connection() as connection:
        connection.execute(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, 'manager', 'test')",
            (username, generate_password_hash(password)),
        )


def test_login_page_loads(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Maintenance Optimizer" in response.data


def test_dashboard_requires_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_rejects_wrong_password(client):
    create_user()
    response = client.post(
        "/login",
        data={"username": "manager", "password": "wrong-password"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Incorrect username or password" in response.data


def test_login_dashboard_and_logout(client, monkeypatch):
    create_user()
    monkeypatch.setattr(dashboard_app, "fetch_machine_summary", lambda: ([], [], "Database not configured for test"))
    monkeypatch.setattr(dashboard_app, "predict_machine_risk", lambda: (None, "Model unavailable in test"))

    response = client.post(
        "/login",
        data={"username": "manager", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")

    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200
    assert b"Machine health dashboard" in dashboard.data

    logout = client.post("/logout")
    assert logout.status_code == 302
    assert logout.headers["Location"].endswith("/login")

    protected = client.get("/dashboard")
    assert protected.status_code == 302
