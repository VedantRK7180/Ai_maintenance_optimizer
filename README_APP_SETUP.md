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

## 5. Run the automated tests

From the repository root with the virtual environment activated:

```powershell
python -m pytest -q
```

The test suite checks Flask authentication and dashboard routes, model-risk handling, CNC What-If feature preparation, sensor validation, and helper features. These tests do not prove that your local MySQL or MongoDB servers are configured correctly; those integrations must be checked separately.

## Model risk interpretation

The shared helper in `ml/model_utils.py` uses the model's class labels to find the failure probability rather than assuming a fixed probability-column order. If a model uses labels that do not clearly identify normal and failure, it raises an error instead of silently reporting a potentially misleading risk. Review the class labels and training target definition for every deployed model.

## What is included

- Login/logout with password hashing, server-side session checks and CSRF protection on forms.
- Manager dashboard for records from `MACHINE`, `SENSOR_READING` and `SENSOR_MEASUREMENT`.
- Clear connection warnings if MySQL is unavailable or the existing schema differs.
- Model-file status indicator for `ml/cnc_model_baseline.joblib`.
- Random Forest risk estimate for the latest available CNC-102 sensor reading, using the same feature preparation approach as `ml/db_predict.py`.
- A read-only maintenance priority planner based on the latest saved AI decisions per machine.
- A CNC What-If simulator that runs the saved model on current and hypothetical sensor inputs; scenario values are illustrative and never saved to the database.
- Optional MongoDB connection settings for the AI decision engine.

## Notes and limitations

- The planner ranks existing saved AI decisions into suggested review windows. It does not create maintenance records, book calendar slots, assign technicians, reserve spare parts, or write to maintenance tables. Those operations must be added only after the exact local schema is verified.
- The CNC What-If simulator runs model inference for both the latest CNC sensor reading and the hypothetical values entered by the manager. Its displayed scenario health is calculated as 100 minus the model risk, while baseline health comes from the latest saved AI decision. The simulator assumes machine type `M` and estimates process temperature as air temperature +10 K because those inputs are not currently stored as independent measurements. Treat these as modelling assumptions, not calibrated or live operational truth. Scenario values are not written to the database.
- The CNC-102 risk estimate depends on the model file, the four expected sensor names, and the database schema being available. It is a model estimate, not a guarantee of failure.
- The MySQL queries assume the table names and columns used by the existing ML script. If your database schema differs, adjust `fetch_machine_summary()` in `app.py`.
- Keep `FLASK_DEBUG=false` outside local development. For deployment, use HTTPS and set `COOKIE_SECURE=true`.
- Manager authentication uses SQLite to avoid making login depend on the factory sensor database being online.
- Do not deploy with the fallback development secret. Set a long random `FLASK_SECRET_KEY` in `.env`.


## Machine monitoring and database explorer

- Open **Machine monitoring** to select a registered machine, inspect its recent sensor history, and plot one sensor's latest numeric trend.
- Optional upper-limit alerts can be configured locally with `SENSOR_THRESHOLDS_JSON` in `.env`. The value must be a JSON object mapping exact sensor names to numeric upper limits, for example `SENSOR_THRESHOLDS_JSON='{"Temperature":80,"Vibration":7.5}'`. This is an illustration only: verify sensor names, units, and limits for your equipment. No default industrial limits are assumed.
- The **Database explorer** is read-only. It displays 25 records per page for each MySQL table and MongoDB collection, with Previous/Next controls and a search field. Search filters records on the currently selected page; move between pages to inspect other records. Counts show the total records in each table/collection.
- Keep local credentials and your real `.env` file out of version control. Only commit placeholder values to `.env.example`.
