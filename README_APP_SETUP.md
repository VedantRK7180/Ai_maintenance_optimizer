# Web dashboard setup

This adds a manager login and dashboard to the existing AI Maintenance Optimizer repository. It keeps manager accounts in a local SQLite file and reads factory machine/sensor data from the existing MySQL database. You do not need to change your MySQL password: put the existing password in your local `.env` file. The ML prediction script and connection test also read credentials from environment variables now.

## 1. Install dependencies

Use Python 3.10+ if possible.

```bash
python -m venv .venv
```

Activate the environment:

- Windows PowerShell: `.venv\Scripts\Activate.ps1`
- macOS/Linux: `source .venv/bin/activate`

Then install:

```bash
pip install -r requirements.txt
```

## 2. Configure environment variables

Copy `.env.example` to `.env`, then set `FLASK_SECRET_KEY` to a random value and enter the existing MySQL host, username, password and database name. Do not commit `.env` to GitHub. The repository's `.gitignore` should keep it out of future commits.

Generate a secret key with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

The existing prediction script uses `MYSQL_PASSWORD` and defaults to `MYSQL_USER=root` and `MYSQL_DATABASE=AI_Maintenance_DB` if those two settings are omitted. The web dashboard expects all four connection settings to be set explicitly.

## 3. Create the manager account

```bash
flask --app app create-admin
```

Enter a username and a password of at least 12 characters when prompted. The password is stored as a one-way hash in `instance/auth.db`, not as plain text.

## 4. Start the dashboard

```bash
flask --app app run
```

Open http://127.0.0.1:5000 and sign in with the manager account.

## What is included

- Login/logout with password hashing, server-side session checks and CSRF protection on forms.
- Manager dashboard for records from `MACHINE`, `SENSOR_READING` and `SENSOR_MEASUREMENT`.
- Clear connection warnings if MySQL is unavailable or the existing schema differs.
- Model-file status indicator for `ml/cnc_model_baseline.joblib`.
- Random Forest risk estimate for the latest available CNC-102 sensor reading, using the same feature preparation approach as `ml/db_predict.py`.

## Notes and limitations

- The dashboard displays database records and the existing model's CNC-102 risk estimate; it does not yet create or optimize maintenance schedules. The risk estimate depends on the model file, the four expected sensor names, and the database schema being available.
- The MySQL queries assume the table names and columns used by the existing ML script. If your database schema differs, adjust `fetch_machine_summary()` in `app.py`.
- Keep `FLASK_DEBUG=false` outside local development. For deployment, use HTTPS and set `COOKIE_SECURE=true`.
- Manager authentication uses SQLite to avoid making login depend on the factory sensor database being online.
- Do not deploy with the fallback development secret. Set a long random `FLASK_SECRET_KEY` in `.env`.
