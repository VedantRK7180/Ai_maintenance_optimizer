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
    monkeypatch.setattr(dashboard_app, "fetch_machine_summary", lambda: ([], [], [], "Database not configured for test"))
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



def test_planner_requires_login(client):
    response = client.get("/planner")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_planner_ranks_saved_decisions(client, monkeypatch):
    create_user()
    decisions = [
        {
            "machine_name": "CNC-101",
            "urgency_score": 35.0,
            "failure_risk": 20.0,
            "health_score": 80.0,
            "urgency_level": "LOW",
            "recommendation": "Monitor",
            "decision_time": "2026-01-01 10:00:00",
            "model_key": "test",
        },
        {
            "machine_name": "CNC-103",
            "urgency_score": 72.0,
            "failure_risk": 81.0,
            "health_score": 19.0,
            "urgency_level": "HIGH",
            "recommendation": "Inspect immediately",
            "decision_time": "2026-01-01 11:00:00",
            "model_key": "test",
        },
    ]
    monkeypatch.setattr(
        dashboard_app,
        "fetch_machine_summary",
        lambda: ([], [], decisions, None),
    )
    client.post(
        "/login",
        data={"username": "manager", "password": "correct-horse-battery-staple"},
    )
    response = client.get("/planner")
    assert response.status_code == 200
    assert b"Maintenance priority planner" in response.data
    assert response.data.index(b"CNC-103") < response.data.index(b"CNC-101")
    assert b"Read-only recommendations" in response.data


def test_simulator_requires_login(client):
    response = client.get("/simulator")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_simulator_runs_model_for_current_and_scenario_sensor_values(client, monkeypatch):
    create_user()
    decisions = [{
        "machine_name": "CNC-103",
        "urgency_score": 72.0,
        "failure_risk": 81.0,
        "health_score": 19.0,
        "urgency_level": "HIGH",
        "recommendation": "Inspect immediately",
        "decision_time": "2026-01-01 11:00:00",
        "model_key": "test",
    }]
    monkeypatch.setattr(dashboard_app, "fetch_machine_summary", lambda: ([], [], decisions, None))
    current = {"Temperature": 50, "RPM": 1500, "Torque": 40, "Tool Wear": 100}
    monkeypatch.setattr(dashboard_app, "fetch_latest_cnc_sensor_values", lambda name: (current, None))
    calls = []
    def fake_predict(values):
        calls.append(values.copy())
        return 30.0 if len(calls) == 1 else 22.5
    monkeypatch.setattr("ml.cnc_what_if.predict_cnc_risk", fake_predict)
    client.post("/login", data={"username": "manager", "password": "correct-horse-battery-staple"})
    response = client.get("/simulator?machine=CNC-103&temperature=45&rpm=1600")
    assert response.status_code == 200
    assert b"Maintenance What-If Simulator" in response.data
    assert b"30.00%" in response.data
    assert b"22.50%" in response.data
    assert b"19.00%" in response.data
    assert b"77.50%" in response.data
    assert calls[1]["Temperature"] == 45
    assert calls[1]["RPM"] == 1600
    assert calls[1]["Torque"] == 40
    assert calls[1]["Tool Wear"] == 100
    assert b"not written back" in response.data


def test_simulator_rejects_out_of_range_scenario_values(client, monkeypatch):
    create_user()
    decisions = [{"machine_name": "CNC-101", "failure_risk": 40, "health_score": 70}]
    monkeypatch.setattr(dashboard_app, "fetch_machine_summary", lambda: ([], [], decisions, None))
    monkeypatch.setattr(
        dashboard_app,
        "fetch_latest_cnc_sensor_values",
        lambda name: ({"Temperature": 50, "RPM": 1500, "Torque": 40, "Tool Wear": 100}, None),
    )
    monkeypatch.setattr("ml.cnc_what_if.predict_cnc_risk", lambda values: 40.0)
    client.post("/login", data={"username": "manager", "password": "correct-horse-battery-staple"})
    response = client.get("/simulator?machine=CNC-101&rpm=-5")
    assert response.status_code == 200
    assert b"must be a finite value" in response.data



def test_simulator_handles_invalid_latest_sensor_values_without_server_error(client, monkeypatch):
    create_user()
    decisions = [{"machine_name": "CNC-101", "failure_risk": 40, "health_score": 70}]
    monkeypatch.setattr(dashboard_app, "fetch_machine_summary", lambda: ([], [], decisions, None))
    monkeypatch.setattr(
        dashboard_app,
        "fetch_latest_cnc_sensor_values",
        lambda name: ({"Temperature": None, "RPM": "not-a-number", "Torque": 40, "Tool Wear": 100}, None),
    )
    monkeypatch.setattr("ml.cnc_what_if.predict_cnc_risk", lambda values: 40.0)
    client.post("/login", data={"username": "manager", "password": "correct-horse-battery-staple"})
    response = client.get("/simulator?machine=CNC-101")
    assert response.status_code == 200
    assert b"latest sensor reading contains invalid values" in response.data
    assert b"40.00%" not in response.data


def test_prediction_errors_do_not_expose_internal_exception_text(client, monkeypatch, caplog):
    class FakeCursor:
        def execute(self, query, params):
            self.params = params

        def fetchall(self):
            return [
                {"sensor_name": "Temperature", "sensor_value": 50},
                {"sensor_name": "RPM", "sensor_value": 1500},
                {"sensor_name": "Torque", "sensor_value": 40},
                {"sensor_name": "Tool Wear", "sensor_value": 100},
            ]

        def close(self):
            pass

    class FakeConnection:
        def cursor(self, dictionary=False):
            return FakeCursor()

        def close(self):
            pass

    monkeypatch.setattr(dashboard_app.MODEL_PATH, "exists", lambda: True)
    monkeypatch.setattr(dashboard_app, "get_mysql_connection", lambda: (FakeConnection(), None))
    monkeypatch.setattr(
        "joblib.load",
        lambda path: (_ for _ in ()).throw(RuntimeError("private model path and internal details")),
    )

    prediction, error = dashboard_app.predict_machine_risk("CNC-101")

    assert prediction is None
    assert error == "Prediction could not be calculated. Check the model, sensor data, and server logs."
    assert "private model path and internal details" not in error
    assert "Machine risk prediction failed" in caplog.text

