#!/usr/bin/env python3
import os
import sqlite3
import logging
import datetime
import time

from hal import hal_led as led
from hal import hal_lcd as LCD
from hal import hal_rfid_reader as rfid_reader

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database file path
DB_FILE = os.getenv("DB_PATH", "vending_machine.db")

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def record_rfid_transaction(user_id, price, rfid_card_id, item_id=1):
    """
    Records an RFID transaction in the database:
      - Deducts the payment amount from the user's credit.
      - Inserts an order record with source 'RFID', a generated transaction_id, and the rfid_card_id.
      - Inserts a corresponding sales record.
      
    Parameters:
      user_id (int): The user's ID.
      price (float): The price of the item.
      rfid_card_id (str): The RFID card identifier.
      item_id (int): The ID of the purchased item (default is 1).
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
        cursor.execute("""
            INSERT INTO orders (item_id, source, status, timestamp, transaction_id, rfid_card_id)
            VALUES (?, 'RFID', 'Completed', ?, ?, ?)
        """, (item_id, current_timestamp, transaction_id, rfid_card_id))
        order_id = cursor.lastrowid
        
        # Insert a corresponding record in the sales table.
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

def simulate_rfid_payment(payment_amount):
    """
    Simulate an RFID payment transaction.
    For demonstration purposes, this function simulates a transaction:
      - It returns a test RFID card ID and calculates a new balance.
    """
    # Example simulation logic:
    new_balance = 100.0 - payment_amount  # Simulate deduction from an initial balance
    test_rfid_card_id = "ABC123DEF456"      # Example RFID card ID
    return test_rfid_card_id, new_balance


def main():
    # Initialize LCD and LED
    lcd = LCD.lcd()
    led.init()
    
    # Turn on backlight and clear the display
    lcd.backlight(1)
    lcd.lcd_clear()
    
    # Display a welcome message on LCD line 1
    lcd.lcd_display_string("Tap RFID card", 1)
    
    # Set LED to a default state
    led.set_output(0, 0)
    
    # Initialize the RFID card reader
    reader = rfid_reader.init()
    
    # Infinite loop to scan for RFID cards and process payment
    while True:
        card_id = reader.read_id_no_block()
        card_id = str(card_id)
        
        if card_id != "None":
            logger.info("RFID card ID detected: %s", card_id)
            # Display the RFID card ID on the LCD
            lcd.lcd_display_string("ID: " + card_id, 2)
            
            # Simulate a payment:
            # In this example, we assume:
            #   - user_id is 1 (e.g., John Doe is logged in)
            #   - item_id is 1 (the first menu item is purchased)
            #   - Payment amount is fixed (e.g., $2.50)
            payment_amount = 2.50
            user_id = 1  # Replace with your actual user ID from the login session
            
            # Update the database with the RFID transaction
            record_rfid_transaction(user_id, payment_amount, card_id, item_id=1)
            
            # Optionally, display confirmation on the LCD
            lcd.lcd_clear()
            lcd.lcd_display_string("Payment Successful", 1)
            time.sleep(2)
            lcd.lcd_clear()
            lcd.lcd_display_string("Tap RFID card", 1)
            
            # Wait a bit to avoid multiple deductions for one swipe
            time.sleep(3)
        time.sleep(0.1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("RFID payment simulation terminated.")
