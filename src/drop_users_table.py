import sqlite3
import logging

# Configure logging to include timestamp, level, and message
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

db_path = 'vending_machine.db'  # Path to the SQLite database file (modify if needed)
conn = None
try:
    # 1. Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    logging.info(f"Connected to database at {db_path}")

    # 2. Check if 'users' table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
    table = cursor.fetchone()
    if table:  # If a result is returned, the table exists
        # 3. Drop the 'users' table
        cursor.execute("DROP TABLE users;")
        # 4. Commit the changes
        conn.commit()
        logging.info("Table 'users' dropped successfully.")
    else:
        logging.info("Table 'users' does not exist. No action taken.")

except sqlite3.Error as e:
    # 6. Handle errors gracefully
    logging.error(f"Error while dropping table: {e}")

finally:
    # 5. Close the connection
    if conn:
        conn.close()
        logging.info("Database connection closed.")
