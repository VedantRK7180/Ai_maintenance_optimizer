from pymongo import MongoClient


# ============================================================
# MONGODB SETTINGS
# ============================================================

MONGO_URI = "mongodb://localhost:27017/"

DATABASE_NAME = "AI_Maintenance_Mongo"

COLLECTION_NAME = "WHAT_IF_SCENARIOS"


# ============================================================
# CONNECT TO MONGODB
# ============================================================

print("=" * 70)
print("FIX WHAT-IF MONGODB RECORD")
print("=" * 70)

print()
print("Connecting to MongoDB...")

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000
)

client.admin.command("ping")

db = client[DATABASE_NAME]

collection = db[COLLECTION_NAME]

print("MongoDB connected successfully.")


# ============================================================
# DOCUMENT TO FIX
# ============================================================

document_id = "6ac2dd56663646662dc5e8fd"


# ============================================================
# FIND DOCUMENT
# ============================================================

from bson.objectid import ObjectId


document = collection.find_one(
    {
        "_id": ObjectId(document_id)
    }
)


if document is None:

    print()
    print("Document not found.")

    client.close()

    exit()


print()
print("Document found.")

print(
    "Current urgency level:",
    document["ai_results"]["current"]["urgency_level"]
)


# ============================================================
# UPDATE WRONG VALUE
# ============================================================

result = collection.update_one(
    {
        "_id": ObjectId(document_id)
    },
    {
        "$set": {
            "ai_results.current.urgency_level": "MEDIUM"
        }
    }
)


# ============================================================
# VERIFY UPDATE
# ============================================================

if result.modified_count == 1:

    print()
    print("SUCCESS: Document updated.")

else:

    print()
    print("No modification was required.")


updated_document = collection.find_one(
    {
        "_id": ObjectId(document_id)
    }
)


print()
print("=" * 70)
print("UPDATED RECORD")
print("=" * 70)

print()

print(
    "Machine:",
    updated_document["machine"]["machine_name"]
)

print(
    "Changed Sensor:",
    updated_document["scenario"]["changed_sensor"]
)

print(
    "Current Urgency Score:",
    updated_document["ai_results"]["current"]["urgency_score"]
)

print(
    "Current Urgency Level:",
    updated_document["ai_results"]["current"]["urgency_level"]
)

print(
    "Scenario Urgency Score:",
    updated_document["ai_results"]["what_if"]["urgency_score"]
)

print(
    "Scenario Urgency Level:",
    updated_document["ai_results"]["what_if"]["urgency_level"]
)


# ============================================================
# CLOSE CONNECTION
# ============================================================

client.close()

print()
print("MongoDB connection closed.")

print()
print("=" * 70)
print("FIX COMPLETED")
print("=" * 70)