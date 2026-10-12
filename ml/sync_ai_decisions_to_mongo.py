import mysql.connector
from pymongo import MongoClient


# ============================================================
# DATABASE SETTINGS
# ============================================================

MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = "#123Vrk7"
MYSQL_DATABASE = "AI_Maintenance_DB"

MONGO_URL = "mongodb://localhost:27017/"
MONGO_DATABASE = "AI_Maintenance_Mongo"
MONGO_COLLECTION = "AI_Event_Log"


print("=" * 70)
print("AI MAINTENANCE OPTIMIZER")
print("MYSQL -> MONGODB AI EVENT SYNCHRONIZATION")
print("=" * 70)


mysql_connection = None
mongo_client = None


try:

    # ========================================================
    # CONNECT TO MYSQL
    # ========================================================

    print()
    print("Connecting to MySQL...")

    mysql_connection = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )

    print("MySQL connected successfully.")


    # ========================================================
    # CONNECT TO MONGODB
    # ========================================================

    print()
    print("Connecting to MongoDB...")

    mongo_client = MongoClient(
        MONGO_URL,
        serverSelectionTimeoutMS=5000
    )

    mongo_client.admin.command("ping")

    mongo_db = mongo_client[MONGO_DATABASE]
    mongo_collection = mongo_db[MONGO_COLLECTION]

    print("MongoDB connected successfully.")


    # ========================================================
    # GET LATEST AI DECISION FOR EACH MACHINE
    # ========================================================

    print()
    print("=" * 70)
    print("READING LATEST AI DECISIONS FROM MYSQL")
    print("=" * 70)

    cursor = mysql_connection.cursor(dictionary=True)

    query = """
        SELECT
            d.decision_id,
            d.machine_id,
            m.machine_name,
            mt.type_name AS machine_type,
            d.decision_time,
            d.failure_risk,
            d.health_score,
            d.urgency_score,
            d.urgency_level,
            d.recommendation,
            d.model_key
        FROM AI_DECISION d
        JOIN MACHINE m
            ON d.machine_id = m.machine_id
        JOIN MACHINE_TYPE mt
            ON m.machine_type_id = mt.machine_type_id
        INNER JOIN (
            SELECT
                machine_id,
                MAX(decision_id) AS latest_decision_id
            FROM AI_DECISION
            GROUP BY machine_id
        ) latest
            ON d.decision_id = latest.latest_decision_id
        ORDER BY d.machine_id;
    """

    cursor.execute(query)

    decisions = cursor.fetchall()

    cursor.close()


    print()
    print("Latest AI decisions found:", len(decisions))


    # ========================================================
    # SEND EACH DECISION TO MONGODB
    # ========================================================

    print()
    print("=" * 70)
    print("SYNCHRONIZING AI DECISIONS")
    print("=" * 70)

    inserted_count = 0
    updated_count = 0


    for decision in decisions:

        document = {
            "source": "MySQL_AI_DECISION",

            "source_decision_id": decision["decision_id"],

            "machine": {
                "machine_id": decision["machine_id"],
                "machine_name": decision["machine_name"],
                "machine_type": decision["machine_type"]
            },

            "event_type": "ai_maintenance_decision",

            "prediction": {
                "failure_risk": float(decision["failure_risk"]),
                "health_score": float(decision["health_score"]),
                "urgency_score": float(decision["urgency_score"]),
                "urgency_level": decision["urgency_level"]
            },

            "recommendation": decision["recommendation"],

            "model": {
                "model_key": decision["model_key"]
            },

            "decision_time": decision["decision_time"]
        }


        # ----------------------------------------------------
        # Avoid duplicate documents
        # ----------------------------------------------------

        existing = mongo_collection.find_one({
            "source_decision_id": decision["decision_id"]
        })


        if existing:

            mongo_collection.update_one(
                {
                    "source_decision_id": decision["decision_id"]
                },
                {
                    "$set": document
                }
            )

            updated_count += 1

            print(
                "UPDATED |",
                decision["machine_name"],
                "| Decision ID:",
                decision["decision_id"]
            )

        else:

            mongo_collection.insert_one(document)

            inserted_count += 1

            print(
                "INSERTED |",
                decision["machine_name"],
                "| Decision ID:",
                decision["decision_id"]
            )


    # ========================================================
    # FINAL RESULT
    # ========================================================

    print()
    print("=" * 70)
    print("SYNCHRONIZATION COMPLETED")
    print("=" * 70)

    print()
    print("New documents inserted :", inserted_count)
    print("Existing documents updated:", updated_count)

    total_documents = mongo_collection.count_documents({})

    print("Total MongoDB documents:", total_documents)

    print()
    print("SUCCESS: MySQL AI decisions synchronized with MongoDB.")


except Exception as e:

    print()
    print("=" * 70)
    print("SYNCHRONIZATION FAILED")
    print("=" * 70)

    print()
    print("Error:", e)


finally:

    if mysql_connection is not None:
        mysql_connection.close()
        print()
        print("MySQL connection closed.")

    if mongo_client is not None:
        mongo_client.close()
        print("MongoDB connection closed.")