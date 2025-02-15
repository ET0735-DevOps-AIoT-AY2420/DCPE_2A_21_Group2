#!/usr/bin/env python3
import os
import sqlite3
import logging
import datetime
import time

from hal import hal_led as led
from hal import hal_lcd as LCD
from hal import hal_rfid_reader as rfid_reader
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_FILE = os.getenv("DB_PATH", "/data/vending_machine.db")

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def simulate_rfid_payment(payment_amount, timeout=30):
    """
    Waits for up to `timeout` seconds for an RFID card scan.
    In this simulation, after 5 seconds a test card is detected.
    Returns (rfid_card_id, new_balance) if detected; otherwise, (None, None).
    """
    logger.info("Waiting for RFID card scan for up to %s seconds...", timeout)
    start_time = time.time()
    while time.time() - start_time < timeout:
        elapsed = time.time() - start_time
        if elapsed >= 5:
            new_balance = 100.0 - payment_amount  # simulate deduction from an initial balance
            test_rfid_card_id = "ABC123DEF456"
            logger.info("RFID card detected after %.2f seconds.", elapsed)
            return test_rfid_card_id, new_balance
        time.sleep(1)
    logger.warning("RFID card scan timed out after %s seconds.", timeout)
    return None, None

def record_rfid_transaction(user_id, price, rfid_card_id, item_id=1):
    """
    Records an RFID transaction:
      - Deducts the payment amount from the user's credit.
      - Inserts an order record with source 'RFID', a generated transaction_id, and the RFID card ID.
      - Inserts a corresponding sales record.
    """
    current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET credit = credit - ? WHERE user_id = ?", (price, user_id))
        transaction_id = str(datetime.datetime.now().timestamp())
        cursor.execute("""
            INSERT INTO orders (item_id, source, status, timestamp, transaction_id, rfid_card_id)
            VALUES (?, 'RFID', 'Completed', ?, ?, ?)
        """, (item_id, current_timestamp, transaction_id, rfid_card_id))
        order_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO sales (order_id, item_id, timestamp, price, source)
            VALUES (?, ?, ?, ?, 'RFID')
        """, (order_id, item_id, current_timestamp, price))
        conn.commit()
        logger.info("RFID transaction recorded: Order ID %s for RFID card %s.", order_id, rfid_card_id)
    except Exception as e:
        conn.rollback()
        logger.error("Error recording RFID transaction: %s", e)
    finally:
        conn.close()

if __name__ == "__main__":
    # For standalone testing of the RFID simulation
    test_card, test_balance = simulate_rfid_payment(payment_amount=2.50, timeout=30)
    print("Test RFID Card:", test_card, "New Balance:", test_balance)