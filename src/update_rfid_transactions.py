#!/usr/bin/env python3
import os
import sqlite3
import logging
import datetime
import bcrypt

# Configure logging to include timestamp, level, and message
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database file (adjust if needed)
DB_FILE = os.environ.get("DB_PATH", "vending_machine.db")

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def update_orders_schema(db_file):
    """
    Ensures that the orders table has a column named 'rfid_card_id'
    for storing the RFID card ID used in a transaction.
    Also ensures the 'source' column exists.
    """
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check existing columns in the orders table.
    cursor.execute("PRAGMA table_info(orders)")
    columns = [col["name"] for col in cursor.fetchall()]
    
    if "rfid_card_id" not in columns:
        try:
            cursor.execute("ALTER TABLE orders ADD COLUMN rfid_card_id TEXT")
            conn.commit()
            logger.info("Added 'rfid_card_id' column to orders table.")
        except sqlite3.OperationalError as e:
            logger.error("Error adding 'rfid_card_id' column: %s", e)
    else:
        logger.info("'rfid_card_id' column already exists in orders table.")
    
    if "source" not in columns:
        try:
            cursor.execute("ALTER TABLE orders ADD COLUMN source TEXT")
            conn.commit()
            logger.info("Added 'source' column to orders table.")
        except sqlite3.OperationalError as e:
            logger.error("Error adding 'source' column: %s", e)
    else:
        logger.info("'source' column already exists in orders table.")
    conn.close()

def record_rfid_transaction(user_id, item_index, price, rfid_card_id):
    """
    Records an RFID transaction:
      - Deducts the payment amount from the user's credit.
      - Inserts an order record with source 'RFID' and the rfid_card_id.
      - Inserts a corresponding sales record.
    All changes are committed atomically.
    
    Parameters:
      user_id (int): The user's ID.
      item_index (int): Index of the purchased item (0-based).
      price (float): The price of the item.
      rfid_card_id (str): The RFID card identifier.
    """
    current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Deduct the price from the user's credit.
        cursor.execute("UPDATE users SET credit = credit - ? WHERE user_id = ?", (price, user_id))
        
        # Generate a transaction_id using the current timestamp.
        transaction_id = str(datetime.datetime.now().timestamp())
        
        # Insert the RFID transaction into the orders table.
        cursor.execute(
            """
            INSERT INTO orders (item_id, source, status, timestamp, transaction_id, rfid_card_id)
            VALUES (?, 'RFID', 'Completed', ?, ?, ?)
            """,
            (item_index + 1, current_timestamp, transaction_id, rfid_card_id)
        )
        order_id = cursor.lastrowid
        
        # Insert a corresponding record in the sales table.
        cursor.execute(
            """
            INSERT INTO sales (order_id, item_id, timestamp, price, source)
            VALUES (?, ?, ?, ?, 'RFID')
            """,
            (order_id, item_index + 1, current_timestamp, price)
        )
        conn.commit()
        logger.info("RFID transaction recorded: Order ID %s, new credit deducted for RFID card %s.", order_id, rfid_card_id)
    except Exception as e:
        conn.rollback()
        logger.error("Error recording RFID transaction: %s", e)
    finally:
        conn.close()

if __name__ == "__main__":
    # Update the orders schema to include 'rfid_card_id' and 'source' columns.
    update_orders_schema(DB_FILE)
    
    # --- Simulated Test ---
    # For testing purposes, simulate an RFID transaction.
    # In your actual application, you would call record_rfid_transaction
    # with values gathered during the RFID payment process.
    
    # Example test values:
    test_user_id = 1                # Assume the user with ID 1 is logged in.
    test_item_index = 0             # For example, "Classic Coffee" (first item)
    test_price = 2.50               # Payment amount for the item
    test_rfid_card_id = "ABC123DEF456"  # Example RFID card ID
    
    record_rfid_transaction(test_user_id, test_item_index, test_price, test_rfid_card_id)
