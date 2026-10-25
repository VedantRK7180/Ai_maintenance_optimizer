# ============================================================
# AI-DRIVEN HEURISTIC MAINTENANCE SCHEDULER
# AI Risk + Technician + Spare Part Constraints
# ============================================================

import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv()


# ------------------------------------------------------------
# DATABASE CONNECTION
# ------------------------------------------------------------

def connect_database():
    """Connect using the same local .env settings as the AI decision engine."""
    password = os.getenv("MYSQL_PASSWORD", os.getenv("DB_PASSWORD", ""))
    if not password:
        raise RuntimeError(
            "MySQL password is missing. Set MYSQL_PASSWORD (or DB_PASSWORD) in .env."
        )

    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", os.getenv("DB_HOST", "localhost")),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", os.getenv("DB_USER", "root")),
        password=password,
        database=os.getenv("MYSQL_DATABASE", os.getenv("DB_NAME", "AI_Maintenance_DB")),
    )


# ------------------------------------------------------------
# TECHNICIAN SCORE
# ------------------------------------------------------------

def calculate_technician_score(
    technician_specialization,
    machine_type,
    availability_status
):
    score = 0

    if availability_status == "Available":
        score += 50
    else:
        score -= 100

    if machine_type == "CNC Machine":
        if technician_specialization == "CNC":
            score += 40

    elif machine_type == "Robotic Arm":
        if technician_specialization == "Robotics":
            score += 40

    elif machine_type == "Rotating Equipment":
        if technician_specialization == "Rotating Equipment":
            score += 40

    return score


# ------------------------------------------------------------
# TECHNICIAN TIME CONFLICT
# ------------------------------------------------------------

def has_time_conflict(
    technician_id,
    job,
    assigned_jobs
):

    for assigned in assigned_jobs:

        if assigned["technician_id"] != technician_id:
            continue

        if assigned["scheduled_date"] != job["scheduled_date"]:
            continue

        if (
            job["start_time"] < assigned["end_time"]
            and
            job["end_time"] > assigned["start_time"]
        ):
            return True

    return False


# ------------------------------------------------------------
# AI RISK + FUZZY URGENCY
# ------------------------------------------------------------

def calculate_ai_priority_score(
    failure_risk,
    urgency_score
):

    score = 0

    # Failure risk contributes 60%
    score += failure_risk * 0.6

    # Fuzzy urgency contributes 40%
    score += urgency_score * 0.4

    return score


# ------------------------------------------------------------
# GET MAINTENANCE JOBS
# ------------------------------------------------------------

def get_maintenance_jobs(connection):

    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT
        mn.maintenance_id,
        mn.machine_id,
        m.machine_name,
        mt.type_name AS machine_type,

        mn.maintenance_type,
        mn.scheduled_date,
        mn.start_time,
        mn.end_time,
        mn.status,
        mn.priority,

        mr.spare_part_id,
        mr.required_quantity,

        sp.part_name,
        sp.quantity_available,

        ai.failure_risk,
        ai.urgency_score,
        ai.urgency_level

    FROM MAINTENANCE mn

    JOIN MACHINE m
        ON mn.machine_id = m.machine_id

    JOIN MACHINE_TYPE mt
        ON m.machine_type_id = mt.machine_type_id

    LEFT JOIN MAINTENANCE_REQUIREMENT mr
        ON mn.maintenance_type = mr.maintenance_type

    LEFT JOIN SPARE_PART sp
        ON mr.spare_part_id = sp.spare_part_id

    LEFT JOIN (
        SELECT
            d1.machine_id,
            d1.failure_risk,
            d1.urgency_score,
            d1.urgency_level

        FROM AI_DECISION d1

        INNER JOIN (
            SELECT
                machine_id,
                MAX(decision_id) AS latest_decision_id
            FROM AI_DECISION
            GROUP BY machine_id
        ) latest

        ON d1.decision_id = latest.latest_decision_id

    ) ai

    ON mn.machine_id = ai.machine_id

    WHERE mn.status = 'Planned';

    """

    cursor.execute(query)

    jobs = cursor.fetchall()

    cursor.close()

    return jobs


# ------------------------------------------------------------
# GET TECHNICIANS
# ------------------------------------------------------------

def get_technicians(connection):

    cursor = connection.cursor(dictionary=True)

    query = """
    SELECT
        technician_id,
        technician_name,
        specialization,
        availability_status

    FROM TECHNICIAN;
    """

    cursor.execute(query)

    technicians = cursor.fetchall()

    cursor.close()

    return technicians


# ------------------------------------------------------------
# CHECK SPARE AVAILABILITY
# ------------------------------------------------------------

def has_spare_available(job):

    if job["required_quantity"] is None:
        return False

    if job["quantity_available"] is None:
        return False

    return (
        job["quantity_available"]
        >= job["required_quantity"]
    )


# ------------------------------------------------------------
# CHECK EXISTING SPARE RESERVATION
# ------------------------------------------------------------

def already_reserved(
    connection,
    maintenance_id
):

    cursor = connection.cursor(
        dictionary=True
    )

    query = """
    SELECT
        reservation_id

    FROM SPARE_RESERVATION

    WHERE maintenance_id = %s

    AND reservation_status = 'Reserved'

    LIMIT 1;
    """

    cursor.execute(
        query,
        (maintenance_id,)
    )

    result = cursor.fetchone()

    # Clear any unread rows
    cursor.fetchall()

    cursor.close()

    return result is not None


# ------------------------------------------------------------
# RESERVE SPARE PART
# ------------------------------------------------------------

def reserve_spare_part(
    connection,
    maintenance_id,
    spare_part_id,
    quantity
):

    # Check whether already reserved
    if already_reserved(
        connection,
        maintenance_id
    ):

        print(
            "    Spare already reserved."
        )

        return


    cursor = connection.cursor()


    # Insert reservation
    reservation_query = """
    INSERT INTO SPARE_RESERVATION
    (
        maintenance_id,
        spare_part_id,
        quantity_reserved,
        reservation_status
    )

    VALUES
    (
        %s,
        %s,
        %s,
        'Reserved'
    );
    """

    cursor.execute(
        reservation_query,
        (
            maintenance_id,
            spare_part_id,
            quantity
        )
    )


    # Reduce available quantity
    update_query = """
    UPDATE SPARE_PART

    SET quantity_available =
        quantity_available - %s

    WHERE spare_part_id = %s;
    """

    cursor.execute(
        update_query,
        (
            quantity,
            spare_part_id
        )
    )


    connection.commit()

    cursor.close()


# ------------------------------------------------------------
# ASSIGN TECHNICIAN
# ------------------------------------------------------------

def assign_technician(
    connection,
    maintenance_id,
    technician_id
):

    cursor = connection.cursor()

    query = """
    UPDATE MAINTENANCE

    SET technician_id = %s

    WHERE maintenance_id = %s;
    """

    cursor.execute(
        query,
        (
            technician_id,
            maintenance_id
        )
    )

    connection.commit()

    cursor.close()


# ------------------------------------------------------------
# SELECT BEST TECHNICIAN
# ------------------------------------------------------------

def select_best_technician(
    technicians,
    machine_type,
    job,
    assigned_jobs
):

    best_technician = None

    best_score = -999999


    for technician in technicians:

        print(
            f"    {technician['technician_name']}",
            end=""
        )


        # Check time conflict
        if has_time_conflict(
            technician["technician_id"],
            job,
            assigned_jobs
        ):

            print(
                " -> CONFLICT"
            )

            continue


        # Calculate technician score
        score = calculate_technician_score(
            technician["specialization"],
            machine_type,
            technician["availability_status"]
        )


        print(
            f" -> Score: {score}"
        )


        if score > best_score:

            best_score = score

            best_technician = technician


    return (
        best_technician,
        best_score
    )


# ============================================================
# MAIN PROGRAM
# ============================================================

if __name__ == "__main__":

    print(
        "\n========== "
        "AI-DRIVEN HEURISTIC SCHEDULER "
        "==========\n"
    )


    # --------------------------------------------------------
    # CONNECT TO MYSQL
    # --------------------------------------------------------

    try:

        connection = connect_database()

        print(
            "Connected to MySQL."
        )

    except mysql.connector.Error as error:

        print(
            "MySQL connection failed."
        )

        print(
            "Error:",
            error
        )

        exit()


    # --------------------------------------------------------
    # GET JOBS AND TECHNICIANS
    # --------------------------------------------------------

    jobs = get_maintenance_jobs(
        connection
    )

    technicians = get_technicians(
        connection
    )


    print(
        f"\nPlanned maintenance jobs found: "
        f"{len(jobs)}"
    )


    # --------------------------------------------------------
    # CALCULATE AI PRIORITY FOR EACH JOB
    # --------------------------------------------------------

    for job in jobs:

        if job["failure_risk"] is not None:

            failure_risk = float(
                job["failure_risk"]
            )

        else:

            failure_risk = 0


        if job["urgency_score"] is not None:

            urgency_score = float(
                job["urgency_score"]
            )

        else:

            urgency_score = 0


        job["ai_priority_score"] = (
            calculate_ai_priority_score(
                failure_risk,
                urgency_score
            )
        )


    # --------------------------------------------------------
    # SORT JOBS USING AI PRIORITY
    # --------------------------------------------------------

    jobs.sort(
        key=lambda job:
        job["ai_priority_score"],
        reverse=True
    )


    # --------------------------------------------------------
    # TRACK ASSIGNED JOBS
    # --------------------------------------------------------

    assigned_jobs = []


    # ========================================================
    # PROCESS EACH MAINTENANCE JOB
    # ========================================================

    for job in jobs:

        print(
            "\n----------------------------------------"
        )


        print(
            f"\nMaintenance ID : "
            f"{job['maintenance_id']}"
        )

        print(
            f"Machine        : "
            f"{job['machine_name']}"
        )

        print(
            f"Machine Type   : "
            f"{job['machine_type']}"
        )

        print(
            f"Maintenance    : "
            f"{job['maintenance_type']}"
        )

        print(
            f"Database Priority : "
            f"{job['priority']}"
        )

        print(
            f"Time           : "
            f"{job['start_time']} - "
            f"{job['end_time']}"
        )


        # ----------------------------------------------------
        # AI DECISION INFORMATION
        # ----------------------------------------------------

        print(
            "\nAI Decision:"
        )


        if job["failure_risk"] is not None:

            print(
                f"    Failure Risk : "
                f"{float(job['failure_risk']):.2f}%"
            )

            print(
                f"    Urgency Score: "
                f"{float(job['urgency_score']):.2f}"
            )

            print(
                f"    Urgency Level: "
                f"{job['urgency_level']}"
            )

            print(
                f"    AI Priority Score: "
                f"{job['ai_priority_score']:.2f}"
            )

        else:

            print(
                "    No AI decision found."
            )


        # ----------------------------------------------------
        # SPARE PART CHECK
        # ----------------------------------------------------

        print(
            "\nSpare Part Requirement:"
        )


        if job["part_name"] is None:

            print(
                "    No spare part requirement."
            )

            print(
                "    Job cannot be scheduled."
            )

            continue


        print(
            f"    Part      : "
            f"{job['part_name']}"
        )

        print(
            f"    Required  : "
            f"{job['required_quantity']}"
        )

        print(
            f"    Available : "
            f"{job['quantity_available']}"
        )


        if not has_spare_available(job):

            print(
                "\n    SPARE CONSTRAINT FAILED"
            )

            print(
                "    Not enough spare parts."
            )

            print(
                "    Job cannot be scheduled."
            )

            continue


        print(
            "\n    Spare constraint satisfied."
        )


        # ----------------------------------------------------
        # TECHNICIAN SELECTION
        # ----------------------------------------------------

        print(
            "\nTechnician Evaluation:"
        )


        best_technician, best_score = (
            select_best_technician(
                technicians,
                job["machine_type"],
                job,
                assigned_jobs
            )
        )


        if best_technician is None:

            print(
                "\nNO FEASIBLE TECHNICIAN FOUND."
            )

            continue


        # ----------------------------------------------------
        # ASSIGN TECHNICIAN
        # ----------------------------------------------------

        assign_technician(
            connection,
            job["maintenance_id"],
            best_technician["technician_id"]
        )


        # ----------------------------------------------------
        # RESERVE SPARE
        # ----------------------------------------------------

        reserve_spare_part(
            connection,
            job["maintenance_id"],
            job["spare_part_id"],
            job["required_quantity"]
        )


        # ----------------------------------------------------
        # DISPLAY RESULT
        # ----------------------------------------------------

        print(
            "\nSelected Technician:"
        )

        print(
            f"    {best_technician['technician_name']}"
        )

        print(
            f"    Technician Score: "
            f"{best_score}"
        )


        print(
            "\nSpare Part:"
        )

        print(
            f"    {job['part_name']}"
        )

        print(
            f"    Quantity: "
            f"{job['required_quantity']}"
        )


        # ----------------------------------------------------
        # SAVE ASSIGNED JOB
        # ----------------------------------------------------

        assigned_jobs.append(
            {
                "technician_id":
                    best_technician["technician_id"],

                "scheduled_date":
                    job["scheduled_date"],

                "start_time":
                    job["start_time"],

                "end_time":
                    job["end_time"]
            }
        )


    # --------------------------------------------------------
    # CLOSE DATABASE
    # --------------------------------------------------------

    connection.close()

    print(
        "\nMySQL connection closed."
    )

    print(
        "\n================================================\n"
    )