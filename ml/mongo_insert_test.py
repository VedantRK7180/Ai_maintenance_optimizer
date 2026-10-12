from pymongo import MongoClient
from datetime import datetime


print("=" * 60)
print("AI MAINTENANCE OPTIMIZER")
print("MONGODB AI EVENT INSERT TEST")
print("=" * 60)

try:
    # Connect to MongoDB
    client = MongoClient(
        "mongodb://localhost:27017/",
        serverSelectionTimeoutMS=5000
    )

    # Verify connection
    client.admin.command("ping")

    # Select database and collection
    db = client["AI_Maintenance_Mongo"]
    collection = db["AI_Event_Log"]

    # Create sample AI event
    ai_event = {
        "machine_id": "CNC-102",
        "event_type": "failure_prediction",
        "model": "AI4I-RandomForest",
        "failure_risk": 43.0,
        "health_score": 57.0,
        "urgency_score": 61.84,
        "urgency_level": "MEDIUM",
        "recommendation": "Schedule maintenance soon",
        "event_time": datetime.now()
    }

    # Insert document
    result = collection.insert_one(ai_event)

    print()
    print("AI event inserted successfully!")
    print("Document ID:", result.inserted_id)

    print()
    print("Database   :", db.name)
    print("Collection :", collection.name)

    # Count documents
    count = collection.count_documents({})

    print("Total documents:", count)

    client.close()

    print()
    print("MongoDB insert test successful.")

except Exception as e:

    print()
    print("MongoDB operation failed!")
    print("Error:", e)