import os

import mysql.connector
from dotenv import load_dotenv


def main():
    load_dotenv()
    print("\\n========== MYSQL CONNECTION TEST ==========\\n")

    mysql_password = os.getenv("MYSQL_PASSWORD")
    if not mysql_password:
        print("MYSQL_PASSWORD is missing. Add your existing MySQL password to the local .env file.")
        return

    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "root"),
            password=mysql_password,
            database=os.getenv("MYSQL_DATABASE", "AI_Maintenance_DB")
        )

        if connection.is_connected():
            print("Successfully connected to MySQL!")
            print("Database:", os.getenv("MYSQL_DATABASE", "AI_Maintenance_DB"))

        connection.close()
        print("Connection closed.")

    except mysql.connector.Error as error:
        print("MySQL connection failed.")
        print("Error:", error)

    print("\\n===========================================\\n")


if __name__ == "__main__":
    main()
