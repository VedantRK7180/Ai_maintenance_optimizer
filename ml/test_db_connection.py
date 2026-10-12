import mysql.connector

print("\n========== MYSQL CONNECTION TEST ==========\n")

try:
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="#123Vrk7",
        database="AI_Maintenance_DB"
    )

    if connection.is_connected():
        print("Successfully connected to MySQL!")
        print("Database: AI_Maintenance_DB")

    connection.close()
    print("Connection closed.")

except mysql.connector.Error as error:
    print("MySQL connection failed.")
    print("Error:", error)

print("\n===========================================\n")