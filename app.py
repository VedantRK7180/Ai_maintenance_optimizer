import os
import math
import secrets
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect

from ml.model_utils import predict_failure_probability
from werkzeug.security import check_password_hash

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
AUTH_DB = Path(os.getenv("AUTH_DB_PATH", str(BASE_DIR / "instance" / "auth.db")))
MODEL_PATH = BASE_DIR / "ml" / "cnc_model_baseline.joblib"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("COOKIE_SECURE", "false").lower() == "true"
csrf = CSRFProtect(app)


def get_auth_connection():
    AUTH_DB.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(AUTH_DB)
    connection.row_factory = sqlite3.Row
    return connection


def init_auth_db():
    with get_auth_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'manager',
                created_at TEXT NOT NULL
            )
        """)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def get_mysql_connection():
    """Connect to the existing sensor database; support both MYSQL_* and DB_* env names."""
    host = os.getenv("MYSQL_HOST", os.getenv("DB_HOST"))
    user = os.getenv("MYSQL_USER", os.getenv("DB_USER"))
    password = os.getenv("MYSQL_PASSWORD", os.getenv("DB_PASSWORD"))
    database = os.getenv("MYSQL_DATABASE", os.getenv("DB_NAME"))
    port = os.getenv("MYSQL_PORT", "3306")

    if not all((host, user, password, database)):
        return None, "MySQL is not configured yet. Set host, user, password and database in your local .env file."

    try:
        import mysql.connector
        connection = mysql.connector.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database,
            connection_timeout=5,
        )
        return connection, None
    except Exception:
        # Keep connection details in server logs, not in browser responses.
        app.logger.exception("Could not connect to MySQL")
        return None, "Could not connect to MySQL. Check the local database service and configuration."

def fetch_machine_summary():
    """Read machine, sensor, and latest AI decision data without changing the schema."""
    connection, error = get_mysql_connection()
    if connection is None:
        return [], [], [], error

    machines, readings, decisions = [], [], []
    warnings = []
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM MACHINE ORDER BY machine_id")
        machines = cursor.fetchall()

        cursor.execute("""
            SELECT
                m.machine_name,
                sr.reading_id,
                sr.recorded_at,
                sm.sensor_name,
                sm.sensor_value,
                sm.unit
            FROM MACHINE m
            JOIN SENSOR_READING sr ON m.machine_id = sr.machine_id
            JOIN SENSOR_MEASUREMENT sm ON sr.reading_id = sm.reading_id
            ORDER BY sr.recorded_at DESC, sr.reading_id DESC
            LIMIT 100
        """)
        readings = cursor.fetchall()

        try:
            cursor.execute("""
                SELECT
                    d.decision_id,
                    m.machine_name,
                    d.decision_time,
                    d.failure_risk,
                    d.health_score,
                    d.urgency_score,
                    d.urgency_level,
                    d.recommendation,
                    d.model_key
                FROM AI_DECISION d
                JOIN MACHINE m ON m.machine_id = d.machine_id
                JOIN (
                    SELECT machine_id, MAX(decision_time) AS latest_time
                    FROM AI_DECISION
                    GROUP BY machine_id
                ) latest
                  ON latest.machine_id = d.machine_id
                 AND latest.latest_time = d.decision_time
                ORDER BY d.urgency_score DESC, d.failure_risk DESC
                LIMIT 50
            """)
            decisions = cursor.fetchall()
        except Exception:
            app.logger.exception("Could not read AI decisions")
            warnings.append("AI decisions are temporarily unavailable.")

        cursor.close()
        warning = "; ".join(warnings) if warnings else None
        return machines, readings, decisions, warning
    except Exception:
        app.logger.exception("Could not read machine and sensor tables")
        return [], [], [], "Could not read the expected machine/sensor tables. Check the database schema and logs."
    finally:
        connection.close()


def predict_machine_risk(machine_name="CNC-102"):
    """Run the shared CNC model-input pipeline against the latest sensor reading."""
    if not MODEL_PATH.is_file():
        return None, "Model file ml/cnc_model_baseline.joblib is missing."
    connection, error = get_mysql_connection()
    if connection is None:
        return None, error
    try:
        import joblib
        from ml.cnc_what_if import build_cnc_model_input

        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT sm.sensor_name, sm.sensor_value
            FROM MACHINE m
            JOIN SENSOR_READING sr ON m.machine_id = sr.machine_id
            JOIN SENSOR_MEASUREMENT sm ON sr.reading_id = sm.reading_id
            WHERE m.machine_name = %s
              AND sr.reading_id = (
                  SELECT sr2.reading_id
                  FROM SENSOR_READING sr2
                  WHERE sr2.machine_id = m.machine_id
                  ORDER BY sr2.recorded_at DESC, sr2.reading_id DESC
                  LIMIT 1
              )
            ORDER BY sm.sensor_name
        """, (machine_name,))
        rows = cursor.fetchall()
        cursor.close()
        if not rows:
            return None, f"No sensor readings found for {machine_name}."

        sensor_data = {row["sensor_name"]: row["sensor_value"] for row in rows}
        missing = [name for name in ("Temperature", "RPM", "Torque", "Tool Wear") if name not in sensor_data]
        if missing:
            return None, "Latest reading is missing model inputs: " + ", ".join(missing)

        package = joblib.load(MODEL_PATH)
        if not isinstance(package, dict) or "model" not in package:
            raise ValueError("The CNC model package has an unexpected format.")
        model = package["model"]
        model_features = package.get("features") or list(getattr(model, "feature_names_in_", []))
        if not model_features:
            raise ValueError("The CNC model does not declare its expected input features.")

        input_data = build_cnc_model_input(sensor_data, list(model_features))
        prediction = int(model.predict(input_data)[0])
        risk = predict_failure_probability(model, input_data)
        return {
            "machine_name": machine_name,
            "condition": "FAILURE RISK" if prediction == 1 else "NORMAL",
            "risk": round(risk * 100, 2),
            "temperature": float(sensor_data["Temperature"]),
            "rpm": float(sensor_data["RPM"]),
            "torque": float(sensor_data["Torque"]),
            "tool_wear": float(sensor_data["Tool Wear"]),
        }, None
    except Exception:
        app.logger.exception("Machine risk prediction failed")
        return None, "Prediction could not be calculated. Check the model, sensor data, and server logs."
    finally:
        connection.close()


@app.context_processor
def inject_globals():
    return {"current_year": datetime.now().year}


@app.route("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with get_auth_connection() as connection:
            user = connection.execute(
                "SELECT id, username, password_hash, role FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        flash("Incorrect username or password.", "error")
    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    machines, readings, decisions, db_error = fetch_machine_summary()
    prediction, prediction_error = predict_machine_risk()
    return render_template(
        "dashboard.html",
        machines=machines,
        readings=readings,
        decisions=decisions,
        db_error=db_error,
        prediction=prediction,
        prediction_error=prediction_error,
        model_available=MODEL_PATH.exists(),
    )


@app.route("/planner")
@login_required
def planner():
    """Provide a read-only maintenance priority queue from saved AI decisions."""
    machines, readings, decisions, db_error = fetch_machine_summary()
    priorities = []
    for decision in decisions:
        try:
            urgency = float(decision.get("urgency_score") or 0)
            if not math.isfinite(urgency):
                urgency = 0.0
        except (TypeError, ValueError, OverflowError):
            urgency = 0.0
        try:
            risk = float(decision.get("failure_risk") or 0)
            if not math.isfinite(risk):
                risk = 0.0
        except (TypeError, ValueError, OverflowError):
            risk = 0.0

        level = str(decision.get("urgency_level") or "").strip().upper()
        if level in {"CRITICAL", "HIGH"} or urgency >= 65 or risk >= 75:
            window = "Immediate review"
            priority = "High"
        elif level == "MEDIUM" or urgency >= 40 or risk >= 40:
            window = "Review soon"
            priority = "Medium"
        else:
            window = "Routine monitoring"
            priority = "Routine"

        priorities.append({
            **decision,
            "priority": priority,
            "suggested_window": window,
            "urgency_numeric": urgency,
            "risk_numeric": risk,
        })

    priorities.sort(
        key=lambda item: (
            {"High": 0, "Medium": 1, "Routine": 2}.get(item["priority"], 3),
            -item["urgency_numeric"],
            -item["risk_numeric"],
        )
    )
    return render_template(
        "planner.html",
        priorities=priorities,
        db_error=db_error,
        machine_count=len(machines),
        reading_count=len(readings),
    )


def fetch_latest_cnc_sensor_values(machine_name):
    """Read the latest sensor values for one machine; this query is read-only."""
    connection, error = get_mysql_connection()
    if connection is None:
        return None, error
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT sm.sensor_name, sm.sensor_value
            FROM MACHINE m
            JOIN SENSOR_READING sr ON sr.machine_id = m.machine_id
            JOIN SENSOR_MEASUREMENT sm ON sm.reading_id = sr.reading_id
            WHERE m.machine_name = %s
              AND sr.reading_id = (
                  SELECT MAX(sr2.reading_id)
                  FROM SENSOR_READING sr2
                  WHERE sr2.machine_id = m.machine_id
              )
        """, (machine_name,))
        rows = cursor.fetchall()
        cursor.close()
        values = {row["sensor_name"]: row["sensor_value"] for row in rows}
        required = ("Temperature", "RPM", "Torque", "Tool Wear")
        missing = [name for name in required if name not in values]
        if missing:
            return None, "Latest reading is missing: " + ", ".join(missing)
        return values, None
    except Exception:
        app.logger.exception("Unable to read latest CNC sensor values")
        return None, "Could not read the latest sensor values."
    finally:
        connection.close()


@app.route("/simulator", methods=["GET", "POST"])
@login_required
def simulator():
    """Compare actual model inference on current vs hypothetical CNC sensor values."""
    from ml.cnc_what_if import predict_cnc_risk

    machines, readings, decisions, db_error = fetch_machine_summary()
    decisions = [item for item in decisions if str(item.get("machine_name", "")).upper().startswith("CNC-")]
    selected_name = request.values.get("machine", "").strip()
    selected = next((item for item in decisions if item.get("machine_name") == selected_name), None)
    if selected is None and decisions:
        selected = decisions[0]
    selected_name = selected.get("machine_name", "") if selected else selected_name

    sensor_fields = {
        "temperature": ("Temperature", "Temperature (°C)", -273.15, 500.0),
        "rpm": ("RPM", "Rotational speed (RPM)", 0.0, 100000.0),
        "torque": ("Torque", "Torque (Nm)", 0.0, 10000.0),
        "tool_wear": ("Tool Wear", "Tool wear (min)", 0.0, 100000.0),
    }
    scenario_values = {}
    input_error = None
    current_values = None
    baseline_risk = simulated_risk = baseline_health = simulated_health = None

    if selected:
        current_values, sensor_error = fetch_latest_cnc_sensor_values(selected_name)
        if sensor_error:
            input_error = sensor_error
        else:
            try:
                scenario_values = {
                    "temperature": float(current_values["Temperature"]),
                    "rpm": float(current_values["RPM"]),
                    "torque": float(current_values["Torque"]),
                    "tool_wear": float(current_values["Tool Wear"]),
                }
                for key, (sensor_name, label, minimum, maximum) in sensor_fields.items():
                    value = scenario_values[key]
                    if not math.isfinite(value) or value < minimum or value > maximum:
                        raise ValueError(f"Latest {label.lower()} is outside the supported range.")
            except (TypeError, ValueError, OverflowError):
                app.logger.warning("Latest CNC sensor values are missing, non-numeric, or outside supported bounds for %s", selected_name)
                input_error = "The latest sensor reading contains invalid values. Check the machine data before simulating."
                scenario_values = {}

            if input_error is None:
                for key, (sensor_name, label, minimum, maximum) in sensor_fields.items():
                    raw = request.values.get(key)
                    if raw not in (None, ""):
                        try:
                            value = float(raw)
                            if not math.isfinite(value) or value < minimum or value > maximum:
                                raise ValueError
                            scenario_values[key] = value
                        except (TypeError, ValueError):
                            input_error = f"{label} must be a finite value between {minimum:g} and {maximum:g}."
                            break
                if input_error is None:
                    try:
                        baseline_risk = predict_cnc_risk(current_values)
                        hypothetical = {
                            "Temperature": scenario_values["temperature"],
                            "RPM": scenario_values["rpm"],
                            "Torque": scenario_values["torque"],
                            "Tool Wear": scenario_values["tool_wear"],
                        }
                        simulated_risk = predict_cnc_risk(hypothetical)
                        try:
                            saved_health = float(selected.get("health_score")) if selected.get("health_score") is not None else None
                        except (TypeError, ValueError, OverflowError):
                            saved_health = None
                        baseline_health = round(saved_health, 2) if saved_health is not None and math.isfinite(saved_health) and 0 <= saved_health <= 100 else None
                        simulated_health = round(100.0 - simulated_risk, 2)
                    except Exception:
                        app.logger.exception("CNC what-if model inference failed")
                        input_error = "Model prediction is unavailable. Check the model file and its input features."
    return render_template(
        "simulator.html",
        decisions=decisions,
        selected=selected,
        selected_name=selected_name,
        db_error=db_error,
        input_error=input_error,
        current_values=current_values,
        scenario_values=scenario_values,
        baseline_risk=baseline_risk,
        baseline_health=baseline_health,
        simulated_risk=simulated_risk,
        simulated_health=simulated_health,
    )

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.cli.command("create-admin")
def create_admin():
    """Create or update a manager account interactively."""
    import getpass
    from werkzeug.security import generate_password_hash

    username = input("Manager username: ").strip()
    if not username:
        print("Username cannot be empty.")
        return
    password = getpass.getpass("Password (minimum 12 characters): ")
    if len(password) < 12:
        print("Use a password with at least 12 characters.")
        return
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.")
        return
    with get_auth_connection() as connection:
        connection.execute("""
            INSERT INTO users (username, password_hash, role, created_at)
            VALUES (?, ?, 'manager', ?)
            ON CONFLICT(username) DO UPDATE SET
                password_hash = excluded.password_hash,
                role = 'manager'
        """, (username, generate_password_hash(password), datetime.utcnow().isoformat()))
    print("Manager account saved. Keep the password private.")


init_auth_db()

if not os.getenv("FLASK_SECRET_KEY"):
    print("WARNING: FLASK_SECRET_KEY is not set. A temporary random key is being used; sessions will reset on restart.")

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
