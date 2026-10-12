import os
import sys
import joblib
import mysql.connector
import pandas as pd


# ============================================================
# PATH SETUP
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ML_DIR = os.path.join(BASE_DIR, "ml")

if ML_DIR not in sys.path:
    sys.path.append(ML_DIR)


# ============================================================
# IMPORT PROJECT AI MODULES
# ============================================================

from fuzzy_logic import calculate_urgency
from bearing_model import predict_latest_bearing


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "#123Vrk7",
    "database": "AI_Maintenance_DB"
}


# ============================================================
# DATABASE CONNECTION
# ============================================================

def connect_database():

    return mysql.connector.connect(
        **DB_CONFIG
    )


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
    AND sr.recorded_at = (
        SELECT MAX(recorded_at)
        FROM SENSOR_READING
        WHERE machine_id = %s
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
# CONVERT SENSOR ROWS TO DICTIONARY
# ============================================================

def sensor_rows_to_dict(rows):

    data = {}

    recorded_at = None

    for row in rows:

        sensor_name = row["sensor_name"]

        sensor_value = row["sensor_value"]

        data[sensor_name] = sensor_value

        if recorded_at is None:

            recorded_at = row["recorded_at"]


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
    #
    # The trained model uses one-hot encoding
    # for the Type column.
    #
    # Therefore:
    #
    # Type_H
    # Type_L
    # Type_M
    #
    # Current CNC machine type is M.
    #
    # Therefore:
    #
    # H = 0
    # L = 0
    # M = 1
    #
    # --------------------------------------------------------

    all_features = {

        "Type_H": 0,

        "Type_L": 0,

        "Type_M": 1,

        "Air temperature [K]":
            air_temperature,

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


        # Check that every feature expected by
        # the model exists.

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
    # --------------------------------------------------------

    if hasattr(
        model,
        "predict_proba"
    ):

        probabilities = model.predict_proba(X)[0]


        if len(probabilities) == 2:

            failure_risk = float(
                probabilities[1]
            )

        else:

            failure_risk = float(
                prediction
            )


    else:

        failure_risk = float(
            prediction
        )


    # --------------------------------------------------------
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
    sensor_data
):

    model = extract_model(
        model_object
    )


    position = sensor_data.get(
        "Position"
    )

    temperature = sensor_data.get(
        "Temperature"
    )

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
    # TEMPORAL FEATURES
    # --------------------------------------------------------
    #
    # The improved robot model expects historical
    # features.
    #
    # Since the current database reading is a single
    # reading:
    #
    # change = 0
    # rolling mean = current value
    # rolling std = 0
    #
    # --------------------------------------------------------

    X = pd.DataFrame(
        [[

            position,

            temperature,

            voltage,

            0.0,

            0.0,

            0.0,

            position,

            temperature,

            voltage,

            0.0,

            0.0,

            0.0

        ]],
        columns=[

            "position",

            "temperature",

            "voltage",

            "position_change",

            "temperature_change",

            "voltage_change",

            "position_rolling_mean",

            "temperature_rolling_mean",

            "voltage_rolling_mean",

            "position_rolling_std",

            "temperature_rolling_std",

            "voltage_rolling_std"
        ]
    )


    # --------------------------------------------------------
    # PREDICT
    # --------------------------------------------------------

    prediction = model.predict(X)[0]


    # --------------------------------------------------------
    # FAILURE PROBABILITY
    # --------------------------------------------------------

    if hasattr(
        model,
        "predict_proba"
    ):

        probabilities = model.predict_proba(X)[0]


        if len(probabilities) == 2:

            failure_risk = float(
                probabilities[1]
            )

        else:

            failure_risk = float(
                prediction
            )


    else:

        failure_risk = float(
            prediction
        )


    health_score = (
        1 - failure_risk
    ) * 100


    failure_risk_percent = (
        failure_risk * 100
    )


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
# RECOMMENDATION
# ============================================================

def generate_recommendation(
    failure_risk,
    urgency_level,
    condition
):

    if failure_risk >= 70:

        return (
            "Schedule maintenance immediately"
        )


    elif urgency_level == "HIGH":

        return (
            "Schedule maintenance immediately"
        )


    elif failure_risk >= 50:

        return (
            "Schedule maintenance soon"
        )


    elif urgency_level == "MEDIUM":

        return (
            "Schedule maintenance soon"
        )


    else:

        return (
            "Continue monitoring"
        )


# ============================================================
# SAVE AI DECISION
# ============================================================

def save_ai_decision(
    connection,
    machine_id,
    failure_risk,
    health_score,
    urgency_score,
    urgency_level,
    recommendation,
    model_key
):

    cursor = connection.cursor()


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


    cursor.execute(
        query,
        (
            machine_id,
            failure_risk,
            health_score,
            urgency_score,
            urgency_level,
            recommendation,
            saved_model_key
        )
    )


    connection.commit()

    cursor.close()


# ============================================================
# PROCESS ONE MACHINE
# ============================================================

def process_machine(
    connection,
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
            f"Failure Risk : {failure_risk:.2f}%"
        )


        print(
            f"Health Score : {health_score:.2f}%"
        )


        print(
            f"Condition    : {condition}"
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
            machine_id,
            failure_risk,
            health_score,
            urgency_score,
            urgency_level,
            recommendation,
            model_key
        )


        print(
            "AI decision saved to MySQL."
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

            (
                failure_risk,
                health_score,
                condition
            ) = predict_robot(
                model_object,
                sensor_data
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
    # SAVE TO MYSQL
    # ========================================================

    save_ai_decision(
        connection,
        machine_id,
        failure_risk,
        health_score,
        urgency_score,
        urgency_level,
        recommendation,
        model_key
    )


    print(
        "AI decision saved to MySQL."
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


    try:

        # ----------------------------------------------------
        # CONNECT
        # ----------------------------------------------------

        connection = (
            connect_database()
        )


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

        if (
            connection is not None
            and connection.is_connected()
        ):

            connection.close()


            print()

            print(
                "Database connection closed."
            )


# ============================================================
# PROGRAM START
# ============================================================

if __name__ == "__main__":

    main()