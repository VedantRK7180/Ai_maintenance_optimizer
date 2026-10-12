from pymongo import MongoClient


def main():
    print("=" * 60)
    print("AI MAINTENANCE OPTIMIZER")
    print("MONGODB CONNECTION TEST")
    print("=" * 60)

    client = None
    try:
        client = MongoClient(
            "mongodb://localhost:27017/",
            serverSelectionTimeoutMS=5000
        )
        client.admin.command("ping")
        db = client["AI_Maintenance_Mongo"]
        collection = db["AI_Event_Log"]
        print("\\nSuccessfully connected to MongoDB!")
        print("Database   :", db.name)
        print("Collection :", collection.name)
        print("\\nMongoDB connection test successful.")
    except Exception as error:
        print("\\nMongoDB connection failed!")
        print("Error:", error)
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    main()
