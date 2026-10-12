from pymongo import MongoClient


print("=" * 60)
print("AI MAINTENANCE OPTIMIZER")
print("MONGODB CONNECTION TEST")
print("=" * 60)

try:
    # Connect to local MongoDB
    client = MongoClient(
        "mongodb://localhost:27017/",
        serverSelectionTimeoutMS=5000
    )

    # Check connection
    client.admin.command("ping")

    print()
    print("Successfully connected to MongoDB!")

    # Select project database
    db = client["AI_Maintenance_Mongo"]

    # Select collection
    collection = db["AI_Event_Log"]

    print("Database   :", db.name)
    print("Collection :", collection.name)

    print()
    print("MongoDB connection test successful.")

    client.close()

except Exception as e:

    print()
    print("MongoDB connection failed!")
    print("Error:", e)