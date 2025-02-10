#!/usr/bin/env python3
import os
import sqlite3
import logging

# Configure logging to include timestamp, level, and message
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Determine the database file path from environment or use default path
db_path = os.getenv("DB_PATH", "vending_machine.db")
logger.info(f"Database file path: {db_path}")

conn = None
try:
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Check existing columns in the 'orders' table
    cursor.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in cursor.fetchall()]  # list of column names
    logger.info(f"Existing columns in orders table: {columns}")

    # 2. Add 'rfid_card_id' column if it does not exist
    if "rfid_card_id" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN rfid_card_id TEXT;")
        conn.commit()  # commit after schema change
        logger.info("Added 'rfid_card_id' column to orders table.")
    else:
        logger.info("'rfid_card_id' column already exists in orders table.")

    # 3. Ensure the 'source' column exists for recording payment method
    # (Re-check schema in case the previous operation modified it)
    cursor.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in cursor.fetchall()]
    if "source" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN source TEXT;")
        conn.commit()
        logger.info("Added 'source' column to orders table.")
    else:
        logger.info("'source' column already exists in orders table.")


    # 4. Final commit and check the updated schema of the orders table
    conn.commit()
    cursor.execute("PRAGMA table_info(orders)")
    final_columns = [col[1] for col in cursor.fetchall()]
    logger.info(f"Final columns in orders table: {final_columns}")

except Exception as e:
    logger.error(f"An error occurred: {e}")
finally:
    if conn:
        conn.close()
        logger.info("Database connection closed.")
