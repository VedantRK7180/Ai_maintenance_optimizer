import os
import secrets
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
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
    """Connect to the existing sensor database; return None if it is not configured."""
    required = ("MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE")
    if not all(os.getenv(key) for key in required):
        return None, "MySQL is not configured yet. Add the database settings to your .env file."
    try:
        import mysql.connector
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE"),
            connection_timeout=5,
        )
        return connection, None
    except Exception as exc:
        # Keep the dashboard usable while the local database is offline.
        return None, f"Could not connect to MySQL: {exc}"


def fetch_machine_summary():
    connection, error = get_mysql_connection()
    if connection is None:
        return [], [], error
    machines, readings = [], []
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
        cursor.close()
        return machines, readings, None
    except Exception as exc:
        return [], [], f"Connected to MySQL, but the expected MACHINE / SENSOR_READING / SENSOR_MEASUREMENT tables could not be read: {exc}"
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
    machines, readings, db_error = fetch_machine_summary()
    return render_template(
        "dashboard.html",
        machines=machines,
        readings=readings,
        db_error=db_error,
        model_available=MODEL_PATH.exists(),
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
