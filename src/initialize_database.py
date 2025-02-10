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

# Determine the database file path from environment or use default path
DB_FILE = os.getenv("DB_PATH", "vending_machine.db")
logger.info(f"Database file path: {DB_FILE}")

# Sample Data

DRINKS_MENU = [
    # Hot Beverages
    {"name": "Classic Coffee", "category": "Hot Beverage", "price": 2.50, "availability": True, "image": "classic_coffee.jpg"},
    {"name": "Strawberry Latte", "category": "Hot Beverage", "price": 3.00, "availability": True, "image": "strawberry_latte.jpg"},
    {"name": "Lychee Milk Tea", "category": "Hot Beverage", "price": 3.50, "availability": True, "image": "lychee_milk_tea.jpg"},
    {"name": "Mocha Strawberry Twist", "category": "Hot Beverage", "price": 4.00, "availability": True, "image": "mocha_strawberry_twist.jpg"},
    {"name": "Lime Infused Coffee", "category": "Hot Beverage", "price": 2.75, "availability": True, "image": "lime_infused_coffee.jpg"},

    # Cold Beverages
    {"name": "Iced Coffee", "category": "Cold Beverage", "price": 3.00, "availability": True, "image": "iced_coffee.jpg"},
    {"name": "Strawberry Iced Latte", "category": "Cold Beverage", "price": 3.50, "availability": True, "image": "strawberry_iced_latte.jpg"},
    {"name": "Lychee Cooler", "category": "Cold Beverage", "price": 3.75, "availability": True, "image": "lychee_cooler.jpg"},
    {"name": "Lime Lychee Refresher", "category": "Cold Beverage", "price": 3.25, "availability": True, "image": "lime_lychee_refresher.jpg"},
    {"name": "Coffee Berry Chill", "category": "Cold Beverage", "price": 4.50, "availability": True, "image": "coffee_berry_chill.jpg"},

    # Soda Mixes
    {"name": "Strawberry Soda Fizz", "category": "Soda Mix", "price": 3.00, "availability": True, "image": "strawberry_soda_fizz.jpg"},
    {"name": "Lime Sparkle", "category": "Soda Mix", "price": 3.00, "availability": True, "image": "lime_sparkle.jpg"},
    {"name": "Lychee Lime Spritz", "category": "Soda Mix", "price": 3.50, "availability": True, "image": "lychee_lime_spritz.jpg"},
    {"name": "Coffee Soda Kick", "category": "Soda Mix", "price": 4.00, "availability": True, "image": "coffee_soda_kick.jpg"},
    {"name": "Strawberry Lychee Sparkler", "category": "Soda Mix", "price": 4.25, "availability": True, "image": "strawberry_lychee_sparkler.jpg"},

    # Smoothies
    {"name": "Strawberry Milk Smoothie", "category": "Smoothie", "price": 3.50, "availability": True, "image": "strawberry_milk_smoothie.jpg"},
    {"name": "Lychee Delight Smoothie", "category": "Smoothie", "price": 3.75, "availability": True, "image": "lychee_delight_smoothie.jpg"},
    {"name": "Tropical Lime Smoothie", "category": "Smoothie", "price": 4.00, "availability": True, "image": "tropical_lime_smoothie.jpg"},
    {"name": "Strawberry Coffee Smoothie", "category": "Smoothie", "price": 4.50, "availability": True, "image": "strawberry_coffee_smoothie.jpg"},
    {"name": "Lychee Strawberry Frost", "category": "Smoothie", "price": 4.25, "availability": True, "image": "lychee_strawberry_frost.jpg"}
]

INVENTORY_LIST = [
    {"inventory_name": "water", "amount": 10},
    {"inventory_name": "ice", "amount": 10},
    {"inventory_name": "milk", "amount": 10},
    {"inventory_name": "coffee", "amount": 10},
    {"inventory_name": "tea", "amount": 10},
    {"inventory_name": "strawberry", "amount": 10},
    {"inventory_name": "lime", "amount": 10},
    {"inventory_name": "lychee", "amount": 10},
    {"inventory_name": "soda", "amount": 10}
]

MENU_INVENTORY_MAPPING = {
    "Classic Coffee": ["water", "coffee"],
    "Strawberry Latte": ["milk", "coffee", "strawberry"],
    "Lychee Milk Tea": ["milk", "lychee", "tea"],
    "Mocha Strawberry Twist": ["water", "milk", "coffee", "strawberry"],
    "Lime Infused Coffee": ["coffee", "lime"],
    "Iced Coffee": ["water", "coffee", "ice"],
    "Strawberry Iced Latte": ["coffee", "milk", "strawberry", "ice"],
    "Lychee Cooler": ["water", "lychee", "ice"],
    "Lime Lychee Refresher": ["water", "lime", "lychee", "ice"],
    "Coffee Berry Chill": ["coffee", "strawberry", "ice"],
    "Strawberry Soda Fizz": ["soda", "strawberry"],
    "Lime Sparkle": ["soda", "lime"],
    "Lychee Lime Spritz": ["soda", "lychee", "lime"],
    "Coffee Soda Kick": ["soda", "coffee"],
    "Strawberry Lychee Sparkler": ["soda", "strawberry", "lychee"],
    "Strawberry Milk Smoothie": ["milk", "strawberry"],
    "Lychee Delight Smoothie": ["milk", "lychee"],
    "Tropical Lime Smoothie": ["milk", "lime"],
    "Strawberry Coffee Smoothie": ["milk", "strawberry", "coffee"],
    "Lychee Strawberry Frost": ["milk", "lychee", "strawberry"]
}

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # --- Create Tables ---
    # Users table: stores customer information, including RFID card ID and available credit.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            rfid_card_id TEXT UNIQUE,
            credit       REAL DEFAULT 100.0
        );
    """)
    
    # Admin users table: stores administrator credentials.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            admin_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL
        );
    """)
    
    # Admin logs table: logs admin actions.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id   INTEGER,
            ip_address TEXT NOT NULL,
            timestamp  DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(admin_id) REFERENCES admin_users(admin_id)
        );
    """)
    
    # Menu table: stores the drinks/menu items.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            category     TEXT NOT NULL,
            price        REAL NOT NULL,
            availability BOOLEAN NOT NULL,
            image        TEXT
        );
    """)
    
    # Inventory list table: stores available inventory items.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory_list (
            inventory_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            inventory_name TEXT NOT NULL,
            amount         INTEGER NOT NULL
        );
    """)
    
    # Menu-Inventory mapping table: links menu items to inventory components.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu_inventory (
            id             INTEGER,
            name           TEXT,
            inventory_id   INTEGER,
            inventory_name TEXT,
            FOREIGN KEY(id) REFERENCES menu(id),
            FOREIGN KEY(inventory_id) REFERENCES inventory_list(inventory_id)
        );
    """)
    
    # Orders table: records each transaction.
    # Note: The orders table now includes additional columns for RFID payments:
    #       - transaction_id: a unique identifier for the transaction.
    #       - rfid_card_id: the RFID card used to make the payment.
    #       - source: indicates the payment method (e.g., 'RFID', 'Stripe', 'QR', etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id        INTEGER NOT NULL,
            source         TEXT NOT NULL,
            status         TEXT NOT NULL DEFAULT 'Pending',
            timestamp      TEXT NOT NULL,
            transaction_id TEXT,
            rfid_card_id   TEXT,
            FOREIGN KEY (item_id) REFERENCES menu(id)
        );
    """)
    
    # Sales table: records individual sale items linked to orders.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            sale_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id  INTEGER NOT NULL,
            item_id   INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            price     REAL NOT NULL,
            source    TEXT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (item_id)  REFERENCES menu(id)
        );
    """)
    
    conn.commit()
    conn.close()
    logger.info("Tables created (or already exist).")
    
    # --- Populate Data ---
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Populate admin_users
    admin_users = [
        ('admin1', '123456'),
        ('admin2', '123456'),
        ('admin3', '123456'),
        ('admin4', '123456')
    ]
    cursor.executemany("""
        INSERT INTO admin_users (username, password)
        VALUES (?, ?)
    """, admin_users)
    logger.info("Inserted %d admin user(s).", len(admin_users))
    
    # Populate admin_logs with an example log
    cursor.execute("""
        INSERT INTO admin_logs (admin_id, ip_address)
        VALUES (1, '127.0.0.1')
    """)
    
    # Populate users table
    users = [
        ("John Doe", "RFID123456", 100.0),
        ("Jane Smith", "RFID654321", 100.0)
    ]
    cursor.executemany("""
        INSERT INTO users (name, rfid_card_id, credit)
        VALUES (?, ?, ?)
    """, users)
    logger.info("Inserted %d user(s).", len(users))
    
    # Populate menu table
    cursor.executemany("""
        INSERT INTO menu (name, category, price, availability, image)
        VALUES (:name, :category, :price, :availability, :image)
    """, DRINKS_MENU)
    logger.info("Inserted %d menu item(s).", len(DRINKS_MENU))
    
    # Populate inventory_list table
    cursor.executemany("""
        INSERT INTO inventory_list (inventory_name, amount)
        VALUES (:inventory_name, :amount)
    """, INVENTORY_LIST)
    logger.info("Inserted %d inventory item(s).", len(INVENTORY_LIST))
    
    # Populate menu_inventory table
    for drink_name, ingredients in MENU_INVENTORY_MAPPING.items():
        cursor.execute("SELECT id FROM menu WHERE name = ?", (drink_name,))
        menu_row = cursor.fetchone()
        if menu_row:
            menu_id = menu_row[0]
            for ingredient in ingredients:
                cursor.execute("SELECT inventory_id FROM inventory_list WHERE inventory_name = ?", (ingredient,))
                inv_row = cursor.fetchone()
                if inv_row:
                    inventory_id = inv_row[0]
                    cursor.execute("""
                        INSERT INTO menu_inventory (id, name, inventory_id, inventory_name)
                        VALUES (?, ?, ?, ?)
                    """, (menu_id, drink_name, inventory_id, ingredient))
    logger.info("Populated menu_inventory table.")
    
    conn.commit()
    conn.close()
    logger.info("Initial data populated.")
    
    # --- Simulated RFID Transaction ---
    # For testing purposes, simulate an RFID transaction:
    # Assume: User with user_id 1 (John Doe) purchases the first menu item.
    simulate_rfid_transaction()

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
        cursor.execute("""
            INSERT INTO orders (item_id, source, status, timestamp, transaction_id, rfid_card_id)
            VALUES (?, 'RFID', 'Completed', ?, ?, ?)
        """, (item_index + 1, current_timestamp, transaction_id, rfid_card_id))
        order_id = cursor.lastrowid
        
        # Insert a corresponding record in the sales table.
        cursor.execute("""
            INSERT INTO sales (order_id, item_id, timestamp, price, source)
            VALUES (?, ?, ?, ?, 'RFID')
        """, (order_id, item_index + 1, current_timestamp, price))
        
        conn.commit()
        logger.info("RFID transaction recorded: Order ID %s for RFID card %s.", order_id, rfid_card_id)
    except Exception as e:
        conn.rollback()
        logger.error("Error recording RFID transaction: %s", e)
    finally:
        conn.close()

def simulate_rfid_transaction():
    """
    Simulate an RFID payment transaction.
    For demonstration purposes, this function simulates a transaction:
      - Assumes user with user_id = 1 (John Doe) is logged in.
      - Uses the first menu item (index 0) with its price.
      - Uses a test RFID card ID.
    """
    test_user_id = 1                # Assume user with ID 1 is logged in.
    test_item_index = 0             # For example, "Classic Coffee" (first item in the menu)
    
    # Retrieve the price for the test item from the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT price FROM menu WHERE id = ?", (test_item_index + 1,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        logger.error("Test menu item not found.")
        return
    test_price = row[0]
    
    test_rfid_card_id = "ABC123DEF456"  # Example RFID card ID
    record_rfid_transaction(test_user_id, test_item_index, test_price, test_rfid_card_id)

if __name__ == "__main__":
    initialize_database()
