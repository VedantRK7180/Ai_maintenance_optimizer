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

from ml.model_utils import classify_failure_prediction, predict_failure_probability
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
        condition = classify_failure_prediction(model.predict(input_data)[0])
        risk = predict_failure_probability(model, input_data)
        return {
            "machine_name": machine_name,
            "condition": condition,
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
    # Maintenance requests are stored separately in MongoDB; keep this view useful
    # even when MongoDB is not configured or temporarily unavailable.
    maintenance_requests = []
    mongo_error = None
    mongo_uri = os.getenv("MONGODB_URI", os.getenv("MONGO_URI"))
    mongo_database = os.getenv("MONGODB_DATABASE", os.getenv("MONGO_DATABASE"))
    if mongo_uri and mongo_database:
        client = None
        try:
            from pymongo import MongoClient
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2500)
            client.admin.command("ping")
            cursor = client[mongo_database]["MAINTENANCE_REQUESTS"].find(
                {}, {"machine_name": 1, "requested_date": 1, "priority": 1,
                     "description": 1, "status": 1, "requested_by": 1, "created_at": 1}
            ).sort([("requested_date", 1), ("created_at", -1)]).limit(100)
            for item in cursor:
                item["_id"] = str(item.get("_id", ""))
                if isinstance(item.get("created_at"), datetime):
                    item["created_at"] = item["created_at"].strftime("%Y-%m-%d %H:%M")
                maintenance_requests.append(item)
        except Exception:
            app.logger.exception("Could not load maintenance requests from MongoDB")
            mongo_error = "Saved maintenance requests could not be loaded. Check MongoDB configuration and server logs."
        finally:
            if client is not None:
                client.close()
    else:
        mongo_error = "MongoDB is not configured; saved maintenance requests are unavailable."

    return render_template(
        "planner.html",
        priorities=priorities,
        maintenance_requests=maintenance_requests,
        mongo_error=mongo_error,
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
                  SELECT sr2.reading_id
                  FROM SENSOR_READING sr2
                  WHERE sr2.machine_id = m.machine_id
                  ORDER BY sr2.recorded_at DESC, sr2.reading_id DESC
                  LIMIT 1
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


@app.route("/database")
@login_required
def database_browser():
    """Read-only browser for existing MySQL tables and MongoDB collections."""
    import json

    mysql_tables = []
    mysql_error = None
    connection, error = get_mysql_connection()
    if connection is None:
        mysql_error = error
    else:
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT TABLE_NAME FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() ORDER BY TABLE_NAME"
            )
            table_names = [row["TABLE_NAME"] for row in cursor.fetchall()]
            for table_name in table_names:
                safe_name = str(table_name).replace("`", "``")
                cursor.execute(f"SELECT * FROM `{safe_name}` LIMIT 100")
                rows = cursor.fetchall()
                columns = [item[0] for item in (cursor.description or [])]
                mysql_tables.append({
                    "name": table_name,
                    "columns": columns,
                    "rows": rows,
                    "shown": len(rows),
                })
            cursor.close()
        except Exception:
            app.logger.exception("Database browser could not read MySQL tables")
            mysql_error = "Could not read MySQL tables. Check the server logs and database permissions."
        finally:
            connection.close()

    mongo_collections = []
    mongo_error = None
    mongo_uri = os.getenv("MONGODB_URI", os.getenv("MONGO_URI"))
    mongo_database = os.getenv("MONGODB_DATABASE", os.getenv("MONGO_DATABASE"))
    if not mongo_uri:
        mongo_error = "MongoDB is not configured. Set MONGODB_URI in your local .env file to display collections."
    else:
        client = None
        try:
            from pymongo import MongoClient
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
            client.admin.command("ping")
            db = client[mongo_database] if mongo_database else client.get_default_database()
            if db is None:
                raise ValueError("Set MONGODB_DATABASE or include the database name in MONGODB_URI.")
            for collection_name in sorted(db.list_collection_names()):
                documents = list(db[collection_name].find({}, limit=100))
                mongo_collections.append({
                    "name": collection_name,
                    "documents": [json.loads(json.dumps(doc, default=str)) for doc in documents],
                    "shown": len(documents),
                })
        except Exception:
            app.logger.exception("Database browser could not read MongoDB collections")
            mongo_error = "Could not read MongoDB collections. Check the URI, database name, and server logs."
        finally:
            if client is not None:
                client.close()

    return render_template(
        "database.html",
        mysql_tables=mysql_tables,
        mysql_error=mysql_error,
        mongo_collections=mongo_collections,
        mongo_error=mongo_error,
        current_year=datetime.now().year,
    )



@app.route("/machines")
@login_required
def machine_monitor():
    """Show individual machine readings and a read-only history view."""
    machines, _readings, decisions, db_error = fetch_machine_summary()
    machine_names = [str(item.get("machine_name")) for item in machines if item.get("machine_name")]
    selected_name = request.args.get("machine", "").strip()
    if selected_name not in machine_names:
        selected_name = machine_names[0] if machine_names else ""
    history = []
    history_error = db_error
    if selected_name:
        connection, connection_error = get_mysql_connection()
        if connection is None:
            history_error = connection_error
        else:
            try:
                cursor = connection.cursor(dictionary=True)
                cursor.execute("""
                    SELECT sr.reading_id, sr.recorded_at, sm.sensor_name, sm.sensor_value, sm.unit
                    FROM MACHINE m
                    JOIN SENSOR_READING sr ON sr.machine_id = m.machine_id
                    JOIN SENSOR_MEASUREMENT sm ON sm.reading_id = sr.reading_id
                    WHERE m.machine_name = %s
                    ORDER BY sr.recorded_at DESC, sr.reading_id DESC
                    LIMIT 500
                """, (selected_name,))
                history = cursor.fetchall()
                cursor.close()
            except Exception:
                app.logger.exception("Could not load machine sensor history")
                history_error = "Could not load history for this machine. Check the database schema and server logs."
            finally:
                connection.close()
    latest = {}
    for reading in reversed(history):
        latest[str(reading.get("sensor_name", ""))] = reading
    sensor_names = sorted({str(row.get("sensor_name")) for row in history if row.get("sensor_name")})
    selected_sensor = request.args.get("sensor", "").strip()
    if selected_sensor not in sensor_names:
        selected_sensor = sensor_names[0] if sensor_names else ""
    chart_rows = []
    for row in reversed(history):
        if str(row.get("sensor_name", "")) != selected_sensor:
            continue
        try:
            value = float(row.get("sensor_value"))
            if math.isfinite(value):
                chart_rows.append({"time": str(row.get("recorded_at") or ""), "value": value})
        except (TypeError, ValueError, OverflowError):
            continue
    chart_rows = chart_rows[-30:]
    chart_points = ""
    if chart_rows:
        values = [item["value"] for item in chart_rows]
        low, high = min(values), max(values)
        spread = high - low or 1.0
        coords = []
        for index, item in enumerate(chart_rows):
            x = 12 + (index * 576 / max(len(chart_rows) - 1, 1))
            y = 126 - ((item["value"] - low) / spread) * 100
            coords.append(f"{x:.1f},{y:.1f}")
        chart_points = " ".join(coords)

    # Optional per-sensor upper limits can be supplied locally as JSON, e.g.
    # SENSOR_THRESHOLDS_JSON={"Temperature":80,"Vibration":7.5}
    # These are user-configured alert limits, not universal safety recommendations.
    configured_thresholds = {}
    threshold_config_error = None
    try:
        raw_thresholds = os.getenv("SENSOR_THRESHOLDS_JSON", "").strip()
        if raw_thresholds:
            parsed = json.loads(raw_thresholds)
            if not isinstance(parsed, dict):
                raise ValueError("Threshold configuration must be a JSON object.")
            for key, raw_value in parsed.items():
                value = float(raw_value)
                if not math.isfinite(value):
                    raise ValueError("Threshold values must be finite numbers.")
                configured_thresholds[str(key)] = value
    except (ValueError, TypeError, json.JSONDecodeError):
        app.logger.warning("Invalid SENSOR_THRESHOLDS_JSON configuration")
        threshold_config_error = "Sensor threshold configuration is invalid; threshold flags are disabled."
        configured_thresholds = {}
    threshold_flags = []
    for sensor_name, row in latest.items():
        if sensor_name not in configured_thresholds:
            continue
        try:
            value = float(row.get("sensor_value"))
            if math.isfinite(value) and value > configured_thresholds[sensor_name]:
                threshold_flags.append({"name": sensor_name, "value": value, "limit": configured_thresholds[sensor_name], "unit": row.get("unit")})
        except (TypeError, ValueError, OverflowError):
            continue

    decision = next((item for item in decisions if item.get("machine_name") == selected_name), None)
    health = decision.get("health_score") if decision else None
    risk = decision.get("failure_risk") if decision else None
    try:
        critical = (float(risk) >= 75) or str(decision.get("urgency_level", "")).upper() == "CRITICAL"
    except (TypeError, ValueError, AttributeError):
        critical = bool(decision and str(decision.get("urgency_level", "")).upper() == "CRITICAL")
    return render_template("machine_monitor.html", machines=machines, machine_names=machine_names,
        selected_name=selected_name, history=history, latest=latest, decision=decision,
        health=health, risk=risk, critical=critical, db_error=history_error,
        sensor_names=sensor_names, selected_sensor=selected_sensor, chart_rows=chart_rows,
        chart_points=chart_points, threshold_flags=threshold_flags,
        configured_thresholds=configured_thresholds, threshold_config_error=threshold_config_error,
        current_year=datetime.now().year, today=datetime.now().date().isoformat())


@app.route("/maintenance/schedule", methods=["POST"])
@login_required
def schedule_maintenance():
    """Save a maintenance request in MongoDB; this does not reserve a real-world slot."""
    machine_name = request.form.get("machine_name", "").strip()
    requested_date = request.form.get("requested_date", "").strip()
    priority = request.form.get("priority", "Normal").strip().title()
    description = request.form.get("description", "").strip()
    if not machine_name or not requested_date or not description:
        flash("Machine, requested date, and maintenance description are required.", "error")
        return redirect(url_for("machine_monitor", machine=machine_name))
    machines, _readings, _decisions, machine_error = fetch_machine_summary()
    registered_names = {str(item.get("machine_name", "")).strip() for item in machines}
    if machine_error or machine_name not in registered_names:
        flash("Choose a registered machine before submitting a maintenance request.", "error")
        return redirect(url_for("machine_monitor"))
    if len(description) > 2000:
        flash("Please keep the maintenance description under 2,000 characters.", "error")
        return redirect(url_for("machine_monitor", machine=machine_name))
    if priority not in {"Critical", "High", "Normal", "Low"}:
        priority = "Normal"
    try:
        requested_dt = datetime.strptime(requested_date, "%Y-%m-%d")
        if requested_dt.date() < datetime.now().date():
            raise ValueError
    except ValueError:
        flash("Choose a valid maintenance date that is not in the past.", "error")
        return redirect(url_for("machine_monitor", machine=machine_name))
    mongo_uri = os.getenv("MONGODB_URI", os.getenv("MONGO_URI"))
    mongo_database = os.getenv("MONGODB_DATABASE", os.getenv("MONGO_DATABASE"))
    if not mongo_uri or not mongo_database:
        flash("MongoDB is not configured. Set MONGODB_URI and MONGODB_DATABASE in .env.", "error")
        return redirect(url_for("machine_monitor", machine=machine_name))
    client = None
    try:
        from pymongo import MongoClient
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        client[mongo_database]["MAINTENANCE_REQUESTS"].insert_one({
            "machine_name": machine_name, "requested_date": requested_date,
            "priority": priority, "description": description, "status": "Requested",
            "requested_by": session.get("username", "manager"), "created_at": datetime.utcnow(),
            "source": "AI Maintenance Optimizer web app",
        })
        flash("Maintenance request saved. Confirm the actual slot with your maintenance team.", "success")
    except Exception:
        app.logger.exception("Could not save maintenance request to MongoDB")
        flash("Could not save the request. Check MongoDB configuration and server logs.", "error")
    finally:
        if client is not None:
            client.close()
    return redirect(url_for("machine_monitor", machine=machine_name))


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
