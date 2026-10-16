import os
import sys
import joblib
import mysql.connector
import pandas as pd
from dotenv import load_dotenv

from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timezone

load_dotenv()


# ============================================================
# PATH SETUP
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

ML_DIR = os.path.join(
    BASE_DIR,
    "ml"
)

if ML_DIR not in sys.path:
    sys.path.append(ML_DIR)

load_dotenv(os.path.join(BASE_DIR, ".env"))


# ============================================================
# IMPORT PROJECT AI MODULES
# ============================================================

from fuzzy_logic import calculate_urgency
from model_utils import predict_failure_probability
from bearing_model import predict_latest_bearing
from model_utils import predict_failure_probability


# ============================================================
# MYSQL DATABASE CONFIGURATION
# ============================================================

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", ""),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "AI_Maintenance_DB"),
    "connection_timeout": int(os.getenv("MYSQL_CONNECT_TIMEOUT", "5")),
    "host": os.getenv("MYSQL_HOST", os.getenv("DB_HOST", "localhost")),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", os.getenv("DB_USER", "root")),
    "password": os.getenv("MYSQL_PASSWORD", os.getenv("DB_PASSWORD", "")),
    "database": os.getenv("MYSQL_DATABASE", os.getenv("DB_NAME", "AI_Maintenance_DB")),
}

if not DB_CONFIG["password"]:
    raise RuntimeError(
        "MySQL password is missing. Set MYSQL_PASSWORD (or DB_PASSWORD) in your local .env file."
    )


# ============================================================
# MONGODB CONFIGURATION
# ============================================================

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

MONGO_DATABASE = os.getenv("MONGO_DATABASE", "AI_Maintenance_Mongo")

MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "AI_Event_Log")


# ============================================================
# MYSQL CONNECTION
# ============================================================

def connect_database():

    if not DB_CONFIG["user"] or not DB_CONFIG["password"]:
        raise RuntimeError(
            "Set MYSQL_USER and MYSQL_PASSWORD in your .env file before running the AI decision engine."
        )
    return mysql.connector.connect(**DB_CONFIG)


# ============================================================
# MONGODB CONNECTION
# ============================================================

def connect_mongodb():

    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=3000
    )

    # Test connection
    client.admin.command("ping")

    database = client[
        MONGO_DATABASE
    ]

    collection = database[
        MONGO_COLLECTION
    ]

    return client, collection


# ============================================================
# GET ALL MACHINES
# ============================================================

def get_machines(connection):

    cursor = connection.cursor(
        dictionary=True
    )

    query = """
    SELECT
        m.machine_id,
        m.machine_name,
        m.operating_hours,
        m.criticality,
        m.production_importance,
        m.status,
        mt.type_name,
        mt.model_key
    FROM MACHINE m
    JOIN MACHINE_TYPE mt
        ON m.machine_type_id = mt.machine_type_id
    ORDER BY m.machine_id;
    """

    cursor.execute(query)

    machines = cursor.fetchall()

    cursor.close()

    return machines


# ============================================================
# GET LATEST SENSOR DATA
# ============================================================

def get_recent_sensor_history(connection, machine_id, limit=10):
    """Return recent complete sensor readings for robot time-series features."""
    cursor = connection.cursor(dictionary=True)
    query = """
    SELECT sr.reading_id, sr.recorded_at, sm.sensor_name, sm.sensor_value
    FROM SENSOR_READING sr
    JOIN SENSOR_MEASUREMENT sm ON sm.reading_id = sr.reading_id
    JOIN (
        SELECT reading_id, recorded_at
        FROM SENSOR_READING
        WHERE machine_id = %s
        ORDER BY recorded_at DESC, reading_id DESC
        LIMIT %s
    ) recent ON recent.reading_id = sr.reading_id
    ORDER BY sr.recorded_at ASC, sr.reading_id ASC, sm.sensor_name ASC;
    """
    cursor.execute(query, (machine_id, int(limit)))
    rows = cursor.fetchall()
    cursor.close()

    history = {}
    for row in rows:
        reading_id = row["reading_id"]
        item = history.setdefault(reading_id, {
            "reading_id": reading_id,
            "recorded_at": row["recorded_at"],
        })
        item[row["sensor_name"]] = float(row["sensor_value"])
    return list(history.values())


def get_latest_sensor_data(
    connection,
    machine_id
):

    cursor = connection.cursor(
        dictionary=True
    )

    query = """
    SELECT
        sr.reading_id,
        sr.recorded_at,
        sm.sensor_name,
        sm.sensor_value,
        sm.unit
    FROM SENSOR_READING sr
    JOIN SENSOR_MEASUREMENT sm
        ON sr.reading_id = sm.reading_id
    WHERE sr.machine_id = %s
    AND sr.reading_id = (
        SELECT sr2.reading_id
        FROM SENSOR_READING sr2
        WHERE sr2.machine_id = %s
        ORDER BY sr2.recorded_at DESC, sr2.reading_id DESC
        LIMIT 1
    )
      AND sr.reading_id = (
          SELECT sr2.reading_id
          FROM SENSOR_READING sr2
          WHERE sr2.machine_id = %s
          ORDER BY sr2.recorded_at DESC, sr2.reading_id DESC
          LIMIT 1
      )
    ORDER BY sm.sensor_name;
    """

    cursor.execute(
        query,
        (
            machine_id,
            machine_id
        )
    )

    rows = cursor.fetchall()

    cursor.close()

    return rows


# ============================================================
# GET RECENT SENSOR HISTORY FOR ROBOT TIME-SERIES FEATURES
# ============================================================

def get_sensor_history(connection, machine_id, limit=10):
    """Return the most recent readings needed by the robot model."""
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT sr.reading_id, sr.recorded_at,
                   sm.sensor_name, sm.sensor_value
            FROM SENSOR_READING sr
            JOIN SENSOR_MEASUREMENT sm ON sm.reading_id = sr.reading_id
            WHERE sr.machine_id = %s
              AND sr.reading_id IN (
                  SELECT recent.reading_id
                  FROM (
                      SELECT reading_id
                      FROM SENSOR_READING
                      WHERE machine_id = %s
                      ORDER BY recorded_at DESC, reading_id DESC
                      LIMIT %s
                  ) AS recent
              )
            ORDER BY sr.recorded_at ASC, sr.reading_id ASC, sm.sensor_name
            """,
            (machine_id, machine_id, int(limit)),
        )
        rows = cursor.fetchall()
    finally:
        cursor.close()

    if not rows:
        return pd.DataFrame(columns=[
            "reading_id", "recorded_at", "position", "temperature", "voltage"
        ])

    frame = pd.DataFrame(rows)
    frame["sensor_value"] = pd.to_numeric(frame["sensor_value"], errors="coerce")
    frame = frame.pivot_table(
        index=["reading_id", "recorded_at"],
        columns="sensor_name",
        values="sensor_value",
        aggfunc="last",
    ).reset_index()
    frame.columns.name = None
    frame = frame.rename(columns={
        "Position": "position",
        "Temperature": "temperature",
        "Voltage": "voltage",
    })
    required = ["position", "temperature", "voltage"]
    for column in required:
        if column not in frame.columns:
            frame[column] = float("nan")
    frame = frame.dropna(subset=required).copy()
    for column in required:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=required)
    return frame.sort_values(["recorded_at", "reading_id"]).reset_index(drop=True)


# ============================================================
# CONVERT SENSOR ROWS TO DICTIONARY
# ============================================================

def sensor_rows_to_dict(rows):

    data = {}

    recorded_at = None

    for row in rows:

        sensor_name = row[
            "sensor_name"
        ]

        sensor_value = row[
            "sensor_value"
        ]

        data[sensor_name] = sensor_value

        if recorded_at is None:

            recorded_at = row[
                "recorded_at"
            ]

    data["recorded_at"] = recorded_at

    return data


# ============================================================
# TEMPERATURE CONVERSION
# ============================================================

def temperature_to_kelvin(value):

    if value is None:
        return None

    value = float(value)

    # Sensor values below 200 are assumed
    # to be Celsius.

    if value < 200:

        return value + 273.15

    return value


# ============================================================
# LOAD MODEL
# ============================================================

def load_model(model_key):

    # --------------------------------------------------------
    # CNC / AI4I
    # --------------------------------------------------------

    if model_key == "ai4i":

        model_path = os.path.join(
            ML_DIR,
            "cnc_model_baseline.joblib"
        )

        model_object = joblib.load(
            model_path
        )

        return (
            model_object,
            "AI4I-RandomForest"
        )


    # --------------------------------------------------------
    # ROBOT
    # --------------------------------------------------------

    elif model_key == "robot":

        model_path = os.path.join(
            ML_DIR,
            "robot_model_improved.joblib"
        )

        model_object = joblib.load(
            model_path
        )

        return (
            model_object,
            "Robot-RandomForest"
        )


    # --------------------------------------------------------
    # NASA IMS BEARING
    # --------------------------------------------------------

    elif model_key == "bearing":

        return (
            None,
            "NASA_IMS_Bearing"
        )


    else:

        raise ValueError(
            f"Unknown model key: {model_key}"
        )


# ============================================================
# EXTRACT MODEL FROM JOBLIB
# ============================================================

def extract_model(model_object):

    # Model stored directly

    if hasattr(
        model_object,
        "predict"
    ):

        return model_object


    # Model stored inside dictionary

    if isinstance(
        model_object,
        dict
    ):

        possible_keys = [
            "model",
            "classifier",
            "rf_model",
            "random_forest",
            "pipeline"
        ]

        for key in possible_keys:

            if key in model_object:

                candidate = model_object[key]

                if hasattr(
                    candidate,
                    "predict"
                ):

                    return candidate


    raise TypeError(
        "The loaded joblib file does not contain a usable model."
    )


# ============================================================
# CNC PREDICTION
# ============================================================

def predict_cnc(
    model_object,
    sensor_data
):

    model = extract_model(
        model_object
    )


    # --------------------------------------------------------
    # GET SENSOR VALUES
    # --------------------------------------------------------

    air_temperature = sensor_data.get(
        "Temperature"
    )

    rpm = sensor_data.get(
        "RPM"
    )

    torque = sensor_data.get(
        "Torque"
    )

    tool_wear = sensor_data.get(
        "Tool Wear"
    )


    if air_temperature is None:

        raise ValueError(
            "Temperature sensor data missing."
        )


    if rpm is None:

        raise ValueError(
            "RPM sensor data missing."
        )


    if torque is None:

        raise ValueError(
            "Torque sensor data missing."
        )


    if tool_wear is None:

        raise ValueError(
            "Tool Wear sensor data missing."
        )


    # --------------------------------------------------------
    # CONVERT SENSOR VALUES
    # --------------------------------------------------------

    air_temperature = temperature_to_kelvin(
        air_temperature
    )

    process_temperature = (
        air_temperature + 10
    )

    rpm = float(rpm)

    torque = float(torque)

    tool_wear = float(tool_wear)


    # --------------------------------------------------------
    # CREATE ALL POSSIBLE MODEL FEATURES
    # --------------------------------------------------------

    # Current CNC machine type is M.
    #
    # Type_H = 0
    # Type_L = 0
    # Type_M = 1

    all_features = {

        "Type_H": 0,

        "Type_L": 0,

        "Type_M": 1,

        "Air temperature [K]":
            air_temperature,

        # IMPORTANT:
        # Exact feature name used during training.
        "Process temperature [K]":
            process_temperature,

        "Rotational speed [rpm]":
            rpm,

        "Torque [Nm]":
            torque,

        "Tool wear [min]":
            tool_wear
    }


    # --------------------------------------------------------
    # GET EXACT TRAINING FEATURE ORDER
    # --------------------------------------------------------

    if hasattr(
        model,
        "feature_names_in_"
    ):

        trained_features = list(
            model.feature_names_in_
        )

        print(
            f"CNC model features: {trained_features}"
        )


        missing_features = [
            feature
            for feature in trained_features
            if feature not in all_features
        ]


        if missing_features:

            raise ValueError(
                "Missing CNC model features: "
                + str(missing_features)
            )


        X = pd.DataFrame(
            [[
                all_features[feature]
                for feature in trained_features
            ]],
            columns=trained_features
        )


    else:

        # ----------------------------------------------------
        # FALLBACK FEATURE ORDER
        # ----------------------------------------------------

        X = pd.DataFrame(
            [[
                0,
                0,
                1,
                air_temperature,
                process_temperature,
                rpm,
                torque,
                tool_wear
            ]],
            columns=[
                "Type_H",
                "Type_L",
                "Type_M",
                "Air temperature [K]",
                "Process temperature [K]",
                "Rotational speed [rpm]",
                "Torque [Nm]",
                "Tool wear [min]"
            ]
        )


    # --------------------------------------------------------
    # PREDICT
    # --------------------------------------------------------

    prediction = model.predict(X)[0]


    # --------------------------------------------------------
    # FAILURE PROBABILITY

    failure_risk = predict_failure_probability(model, X)

    # --------------------------------------------------------

    failure_risk = predict_failure_probability(model, X)

    # HEALTH SCORE
    # --------------------------------------------------------

    health_score = (
        1 - failure_risk
    ) * 100

    failure_risk_percent = (
        failure_risk * 100
    )


    # --------------------------------------------------------
    # CONDITION
    # --------------------------------------------------------

    if failure_risk_percent >= 50:

        condition = "FAILURE RISK"

    else:

        condition = "NORMAL"


    return (
        failure_risk_percent,
        health_score,
        condition
    )


# ============================================================
# ROBOT PREDICTION
# ============================================================

def predict_robot(
    model_object,
    sensor_data,
    sensor_history=None,
):

    model = extract_model(
        model_object
    )

def predict_robot(model_object, sensor_data, sensor_history=None):
    """Predict robot risk using recent history to match training-time features."""
    model = extract_model(model_object)

    from robot_features import DEFAULT_FEATURES, build_robot_feature_row

    trained_features = None
    if isinstance(model_object, dict):
        trained_features = model_object.get("features")
    if trained_features is None and hasattr(model, "feature_names_in_"):
        trained_features = list(model.feature_names_in_)

    voltage = sensor_data.get(
        "Voltage"
    )


    if position is None:

        raise ValueError(
            "Position sensor data missing."
        )


    if temperature is None:

        raise ValueError(
            "Temperature sensor data missing."
        )


    if voltage is None:

        raise ValueError(
            "Voltage sensor data missing."
        )


    position = float(
        position
    )

    temperature = float(
        temperature
    )

    voltage = float(
        voltage
    )


    # --------------------------------------------------------
    # RECREATE THE SAME TIME-SERIES FEATURES USED IN TRAINING
    # --------------------------------------------------------

    current = {
        "position": position,
        "temperature": temperature,
        "voltage": voltage,
    }

    if sensor_history is None or sensor_history.empty:
        history = pd.DataFrame([current])
    else:
        history = sensor_history[["position", "temperature", "voltage"]].copy()
        history = history.apply(pd.to_numeric, errors="coerce")
        history = history.dropna(subset=["position", "temperature", "voltage"])
        if history.empty:
            history = pd.DataFrame([current])
        else:
            # Ensure the final feature row matches the latest sensor values
            # already retrieved for this machine.
            history.loc[history.index[-1], ["position", "temperature", "voltage"]] = [
                position, temperature, voltage
            ]

    feature_values = dict(current)
    for column in ("position", "temperature", "voltage"):
        values = history[column].tail(10)
        feature_values[f"{column}_change"] = (
            float(values.iloc[-1] - values.iloc[-2]) if len(values) >= 2 else 0.0
        )
        feature_values[f"{column}_rolling_mean"] = float(values.mean())
        rolling_std = values.std(ddof=1) if len(values) >= 2 else 0.0
        feature_values[f"{column}_rolling_std"] = (
            float(rolling_std) if pd.notna(rolling_std) else 0.0
        )

    feature_order = [
        "position", "temperature", "voltage",
        "position_change", "temperature_change", "voltage_change",
        "position_rolling_mean", "temperature_rolling_mean", "voltage_rolling_mean",
        "position_rolling_std", "temperature_rolling_std", "voltage_rolling_std",
    ]
    trained_features = list(getattr(model, "feature_names_in_", feature_order))
    missing_features = [name for name in trained_features if name not in feature_values]
    if missing_features:
        raise ValueError(f"Missing robot model features: {missing_features}")

    X = pd.DataFrame([[feature_values[name] for name in trained_features]],
                     columns=trained_features)


    # --------------------------------------------------------
    # PREDICT
    # --------------------------------------------------------

    prediction = model.predict(X)[0]


    # --------------------------------------------------------
    # FAILURE PROBABILITY

    failure_risk = predict_failure_probability(model, X)


    # HEALTH
    # --------------------------------------------------------

    health_score = (
        1 - failure_risk
    ) * 100

    failure_risk_percent = (
        failure_risk * 100
    )


    # --------------------------------------------------------
    # CONDITION
    # --------------------------------------------------------

    if failure_risk_percent >= 50:

        condition = "FAILURE RISK"

    else:

        condition = "NORMAL"


    return (
        failure_risk_percent,
        health_score,
        condition
    feature_row = build_robot_feature_row(
        sensor_data,
        sensor_history or [],
        feature_names=trained_features,
    )
    if not trained_features:
        trained_features = DEFAULT_FEATURES
    X = pd.DataFrame([[feature_row[name] for name in trained_features]], columns=trained_features)
    failure_risk = predict_failure_probability(model, X)
    failure_risk_percent = failure_risk * 100.0
    health_score = (1.0 - failure_risk) * 100.0
    condition = "FAILURE RISK" if failure_risk_percent >= 50 else "NORMAL"
    return failure_risk_percent, health_score, condition


# ============================================================
# RECOMMENDATION
# ============================================================

def generate_recommendation(
    failure_risk,
    urgency_level,
    condition
):

    if failure_risk >= 70:

        return (
            "Schedule maintenance immediately."
        )


    elif urgency_level == "HIGH":

        return (
            "Schedule maintenance immediately."
        )


    elif failure_risk >= 50:

        return (
            "Schedule maintenance soon."
        )


    elif urgency_level == "MEDIUM":

        return (
            "Schedule maintenance soon."
        )


    else:

        return (
            "Continue monitoring."
        )


# ============================================================
# SAVE AI DECISION TO MYSQL + MONGODB
# ============================================================

def save_ai_decision(
    connection,
    mongo_collection,
    machine,
    failure_risk,
    health_score,
    urgency_score,
    urgency_level,
    recommendation,
    model_key
):

    cursor = connection.cursor()


    # --------------------------------------------------------
    # MYSQL MODEL NAME
    # --------------------------------------------------------

    if model_key == "ai4i":

        saved_model_key = (
            "AI4I-RandomForest"
        )


    elif model_key == "robot":

        saved_model_key = (
            "Robot-RandomForest"
        )


    elif model_key == "bearing":

        saved_model_key = (
            "NASA-IMS-Bearing"
        )


    else:

        saved_model_key = model_key


    # --------------------------------------------------------
    # INSERT INTO MYSQL
    # --------------------------------------------------------

    query = """
    INSERT INTO AI_DECISION
    (
        machine_id,
        decision_time,
        failure_risk,
        health_score,
        urgency_score,
        urgency_level,
        recommendation,
        model_key
    )
    VALUES
    (
        %s,
        NOW(),
        %s,
        %s,
        %s,
        %s,
        %s,
        %s
    );
    """


    cursor.execute(
        query,
        (
            machine["machine_id"],
            failure_risk,
            health_score,
            urgency_score,
            urgency_level,
            recommendation,
            saved_model_key
        )
    )


    connection.commit()


    # --------------------------------------------------------
    # GET MYSQL DECISION ID
    # --------------------------------------------------------

    decision_id = cursor.lastrowid


    cursor.close()


    print(
        f"MySQL AI decision saved. "
        f"Decision ID: {decision_id}"
    )


    # --------------------------------------------------------
    # SAVE AI EVENT TO MONGODB
    # --------------------------------------------------------

    if mongo_collection is not None:

        mongo_document = {

            "source":
                "MySQL_AI_DECISION",

            "source_decision_id":
                int(decision_id),

            "machine": {

                "machine_id":
                    int(machine["machine_id"]),

                "machine_name":
                    machine["machine_name"],

                "machine_type":
                    machine["type_name"]
            },

            "event_type":
                "ai_maintenance_decision",

            "prediction": {

                "failure_risk":
                    float(failure_risk),

                "health_score":
                    float(health_score),

                "urgency_score":
                    float(urgency_score),

                "urgency_level":
                    urgency_level
            },

            "recommendation":
                recommendation,

            "model": {

                "model_key":
                    saved_model_key
            },

            "decision_time":
                datetime.now(timezone.utc)
        }


        mongo_collection.insert_one(
            mongo_document
        )


        print(
            "AI event saved to MongoDB AI_Event_Log."
        )


# ============================================================
# PROCESS ONE MACHINE
# ============================================================

def process_machine(
    connection,
    mongo_collection,
    machine
):

    machine_id = machine[
        "machine_id"
    ]

    machine_name = machine[
        "machine_name"
    ]

    operating_hours = float(
        machine["operating_hours"]
    )

    criticality = machine[
        "criticality"
    ]

    machine_type = machine[
        "type_name"
    ]

    model_key = machine[
        "model_key"
    ]


    print()

    print(
        "----------------------------------------------"
    )

    print(
        f"Machine : {machine_name}"
    )

    print(
        f"Type    : {machine_type}"
    )

    print(
        f"Model   : {model_key}"
    )

    print(
        f"Hours   : {operating_hours:.2f}"
    )

    print(
        f"Criticality : {criticality}"
    )


    # ========================================================
    # NASA IMS BEARING
    # ========================================================

    if model_key == "bearing":

        print(
            "Source  : NASA IMS Bearing Dataset"
        )


        bearing_result = (
            predict_latest_bearing()
        )


        failure_risk = float(
            bearing_result["failure_risk"]
        )

        health_score = float(
            bearing_result["health_score"]
        )

        condition = bearing_result[
            "condition"
        ]


        # ----------------------------------------------------
        # FUZZY LOGIC
        # ----------------------------------------------------

        (
            urgency_score,
            urgency_level
        ) = calculate_urgency(
            failure_risk,
            operating_hours,
            criticality
        )


        # ----------------------------------------------------
        # RULE-BASED DECISION
        # ----------------------------------------------------

        recommendation = (
            generate_recommendation(
                failure_risk,
                urgency_level,
                condition
            )
        )


        # ----------------------------------------------------
        # DISPLAY
        # ----------------------------------------------------

        print(
            f"Failure Risk : "
            f"{failure_risk:.2f}%"
        )

        print(
            f"Health Score : "
            f"{health_score:.2f}%"
        )

        print(
            f"Condition    : "
            f"{condition}"
        )

        print(
            f"Urgency      : "
            f"{urgency_score:.2f} "
            f"({urgency_level})"
        )

        print(
            f"Recommendation : "
            f"{recommendation}"
        )


        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        save_ai_decision(
            connection,
            mongo_collection,
            machine,
            failure_risk,
            health_score,
            urgency_score,
            urgency_level,
            recommendation,
            model_key
        )

        return


    # ========================================================
    # GET SENSOR DATA
    # ========================================================

    sensor_rows = (
        get_latest_sensor_data(
            connection,
            machine_id
        )
    )


    if not sensor_rows:

        print(
            "No sensor data found."
        )

        return


    sensor_data = (
        sensor_rows_to_dict(
            sensor_rows
        )
    )


    print(
        f"Latest reading : "
        f"{sensor_data.get('recorded_at')}"
    )


    # ========================================================
    # LOAD MODEL
    # ========================================================

    try:

        model_object, model_name = (
            load_model(
                model_key
            )
        )


        # ----------------------------------------------------
        # CNC
        # ----------------------------------------------------

        if model_key == "ai4i":

            (
                failure_risk,
                health_score,
                condition
            ) = predict_cnc(
                model_object,
                sensor_data
            )


        # ----------------------------------------------------
        # ROBOT
        # ----------------------------------------------------

        elif model_key == "robot":

            sensor_history_rows = get_sensor_history(
                connection,
                machine_id,
                limit=10,
            )
            sensor_history = sensor_history_rows

            (
                failure_risk,
                health_score,
                condition
            ) = predict_robot(
                model_object,
                sensor_data,
                sensor_history,
                get_recent_sensor_history(connection, machine_id)
            )


        else:

            print(
                f"Unsupported model key: "
                f"{model_key}"
            )

            return


    except Exception as error:

        print(
            f"MODEL ERROR: {error}"
        )

        return


    # ========================================================
    # FUZZY LOGIC
    # ========================================================

    (
        urgency_score,
        urgency_level
    ) = calculate_urgency(
        failure_risk,
        operating_hours,
        criticality
    )


    # ========================================================
    # RULE-BASED RECOMMENDATION
    # ========================================================

    recommendation = (
        generate_recommendation(
            failure_risk,
            urgency_level,
            condition
        )
    )


    # ========================================================
    # DISPLAY
    # ========================================================

    print(
        f"Failure Risk : "
        f"{failure_risk:.2f}%"
    )

    print(
        f"Health Score : "
        f"{health_score:.2f}%"
    )

    print(
        f"Condition    : "
        f"{condition}"
    )

    print(
        f"Urgency      : "
        f"{urgency_score:.2f} "
        f"({urgency_level})"
    )

    print(
        f"Recommendation : "
        f"{recommendation}"
    )


    # ========================================================
    # SAVE TO MYSQL + MONGODB
    # ========================================================

    save_ai_decision(
        connection,
        mongo_collection,
        machine,
        failure_risk,
        health_score,
        urgency_score,
        urgency_level,
        recommendation,
        model_key
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()

    print(
        "=" * 50
    )

    print(
        "        AI MAINTENANCE OPTIMIZER"
    )

    print(
        "        AI DECISION ENGINE"
    )

    print(
        "=" * 50
    )


    connection = None

    mongo_client = None

    mongo_collection = None


    try:

        # ----------------------------------------------------
        # CONNECT TO MYSQL
        # ----------------------------------------------------

        connection = (
            connect_database()
        )

        print()

        print(
            "MySQL connected successfully."
        )


        # ----------------------------------------------------
        # CONNECT TO MONGODB
        # ----------------------------------------------------

        try:

            (
                mongo_client,
                mongo_collection
            ) = connect_mongodb()


            print(
                "MongoDB connected successfully."
            )

            print(
                f"MongoDB collection: "
                f"{MONGO_COLLECTION}"
            )


        except Exception as mongo_error:

            print(
                "MongoDB connection failed."
            )

            print(
                f"MongoDB error: "
                f"{mongo_error}"
            )

            print(
                "Continuing with MySQL only."
            )

            mongo_client = None

            mongo_collection = None


        # ----------------------------------------------------
        # GET MACHINES
        # ----------------------------------------------------

        machines = (
            get_machines(
                connection
            )
        )


        print()

        print(
            f"Machines found: "
            f"{len(machines)}"
        )


        # ----------------------------------------------------
        # PROCESS MACHINES
        # ----------------------------------------------------

        for machine in machines:

            try:

                process_machine(
                    connection,
                    mongo_collection,
                    machine
                )


            except Exception as error:

                print()

                print(
                    f"MACHINE ERROR: "
                    f"{error}"
                )


    except mysql.connector.Error as error:

        print()

        print(
            "DATABASE / SYSTEM ERROR:"
        )

        print(
            error
        )


    except Exception as error:

        print()

        print(
            "SYSTEM ERROR:"
        )

        print(
            error
        )


    finally:

        # ----------------------------------------------------
        # CLOSE MYSQL
        # ----------------------------------------------------

        if (
            connection is not None
            and connection.is_connected()
        ):

            connection.close()

            print()

            print(
                "Database connection closed."
            )


        # ----------------------------------------------------
        # CLOSE MONGODB
        # ----------------------------------------------------

        if mongo_client is not None:

            mongo_client.close()

            print(
                "MongoDB connection closed."
            )


# ============================================================
# PROGRAM START
# ============================================================

if __name__ == "__main__":

    main()
    
