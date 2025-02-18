import sqlite3
import os


# Database file path
DB_FILE = os.getenv("DB_PATH", "/data/vending_machine.db")

# User details
name = "User1"
phone_number = "89150247"
rfid_card_id = "896840044762"
chat_id = "1498916836"
credit = 100.00  # Default starting balance

# Connect to the database
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# Check if user already exists
cursor.execute("SELECT * FROM users WHERE phone_number = ? OR rfid_card_id = ? OR chat_id = ?", 
               (phone_number, rfid_card_id, chat_id))
existing_user = cursor.fetchone()

if existing_user:
    print("Warning: User with this phone number, RFID, or chat ID already exists. No new record added.")
else:
    # Insert user data
    try:
        cursor.execute("""
            INSERT INTO users (name, phone_number, rfid_card_id, chat_id, credit)
            VALUES (?, ?, ?, ?, ?)
        """, (name, phone_number, rfid_card_id, chat_id, credit))
        
        conn.commit()
        print("User inserted successfully!")
    except Exception as e:
        print(f"Error inserting user: {e}")

# Close connection
conn.close()
