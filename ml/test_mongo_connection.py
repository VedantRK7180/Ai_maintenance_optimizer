import os

from dotenv import load_dotenv
from pymongo import MongoClient


def main():
    load_dotenv()
    print("=" * 60)
    print("AI MAINTENANCE OPTIMIZER")
    print("MONGODB CONNECTION TEST")
    print("=" * 60)

    client = None
    try:
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        database_name = os.getenv("MONGO_DATABASE", "AI_Maintenance_Mongo")
        collection_name = os.getenv("MONGO_COLLECTION", "AI_Event_Log")
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        db = client[database_name]
        collection = db[collection_name]
        print("\nSuccessfully connected to MongoDB!")
        print("Database   :", db.name)
        print("Collection :", collection.name)
        print("\nMongoDB connection test successful.")
    except Exception as error:
        print("\nMongoDB connection failed!")
        print("Error:", error)
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    main()
