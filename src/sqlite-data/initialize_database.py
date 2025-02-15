import os
import sqlite3
import logging
import datetime
import uuid
import bcrypt  # For password hashing


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define database file
DB_FILE = os.getenv("DB_PATH", "/data/vending_machine.db")
logger.info(f"Database file path: {DB_FILE}")

# Drinks menu data with images
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
    {"name": "Lychee Strawberry Frost", "category": "Smoothie", "price": 4.25, "availability": True, "image": "lychee_strawberry_frost.jpg"},
]

#Inventory list with amount
INVENTORY_LIST = [
    {"inventory_name": "water", "amount": 10},
    {"inventory_name": "ice", "amount": 10},
    {"inventory_name": "milk", "amount": 10},
    {"inventory_name": "coffee", "amount": 10},
    {"inventory_name": "tea", "amount": 10},
    {"inventory_name": "strawberry", "amount": 10},
    {"inventory_name": "lime", "amount": 10},
    {"inventory_name": "lychee", "amount": 10},
    {"inventory_name": "soda", "amount": 10},
]

#Menu and Inventory
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

# Function to establish a database connection
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# Function to hash passwords
def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt)

# Initialize the database
def initialize_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Create tables

    # Users table: stores customer information, including RFID card ID and available credit.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone_number TEXT UNIQUE NOT NULL,
        chat_id TEXT UNIQUE NOT NULL,
        rfid_card_id TEXT UNIQUE,
        credit REAL DEFAULT 100.0
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

    # Create the admin_logs table to log admin logins
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            ip_address TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES admin_users(id)
        )
    """)

    # Menu table: stores the drinks/menu items.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            availability BOOLEAN NOT NULL,
            image TEXT
        )
    """)

    # Create inventory_list table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory_list (
            inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
            inventory_name TEXT NOT NULL,
            amount INTEGER NOT NULL
        )
    """)

    # Create menu_inventory table : mapping
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu_inventory (
            id INTEGER,
            name TEXT,
            inventory_id INTEGER,
            inventory_name TEXT,
            FOREIGN KEY(id) REFERENCES menu(id),
            FOREIGN KEY(inventory_id) REFERENCES inventory_list(inventory_id) 
        )
    """)

    # Orders table: records each transaction.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,  -- Store user_id instead of phone_number
        source TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        timestamp TEXT NOT NULL,  
        transaction_id TEXT,
        rfid_card_id TEXT,
        FOREIGN KEY (item_id) REFERENCES menu (id),
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
""")


    # Sales table: records individual sale items linked to orders.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales (
    sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    timestamp TEXT NOT NULL,  -- Store time as Singapore Time
    price REAL NOT NULL,
    source TEXT NOT NULL,  -- Local or Remote Order
    payment_source TEXT,  -- NEW: Card, QR, RFID
    FOREIGN KEY (item_id) REFERENCES menu (id),
    FOREIGN KEY (order_id) REFERENCES orders (order_id)
    );
    """)
    
    # Create QR Transactions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS qr_transactions (
            transaction_id TEXT PRIMARY KEY,
            order_id INTEGER NOT NULL,
            phone_number TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            FOREIGN KEY (order_id) REFERENCES orders (order_id)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS collection_qr_codes (
        collection_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        phone_number TEXT NOT NULL,
        chat_id TEXT NOT NULL,
        qr_code TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending', -- Pending | Collected
        timestamp TEXT NOT NULL,  
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
        );
    """)

    # Insert admin users with password '123456'
    admin_users = [
        ('admin1', '123456'),
        ('admin2', '123456'),
        ('admin3', '123456'),
        ('admin4', '123456')
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO admin_users (username, password)
        VALUES (?, ?)
    """, admin_users)
    logger.info("Inserted (or ignored duplicates for) %d admin user(s).", len(admin_users))
    
    # Populate the menu table
    cursor.executemany("""
        INSERT INTO menu (name, category, price, availability, image)
        VALUES (:name, :category, :price, :availability, :image)
    """, DRINKS_MENU)
    logger.info("Inserted (or ignored duplicates for) %d menu item(s).", len(DRINKS_MENU))

    # Populate the inventory_list table
    cursor.executemany(""" 
        INSERT INTO inventory_list(inventory_name, amount)
        VALUES (:inventory_name, :amount)
    """, INVENTORY_LIST)
    logger.info("Inserted (or ignored duplicates for) %d inventory item(s).", len(INVENTORY_LIST))
    
    # Populate menu_inventory table
    for drink_name, ingredients in MENU_INVENTORY_MAPPING.items():
        cursor.execute("SELECT id FROM menu WHERE name = ?", (drink_name,))
        menu_id = cursor.fetchone()
        
        if menu_id:
            menu_id = menu_id[0]
            for ingredient in ingredients:
                cursor.execute("SELECT inventory_id FROM inventory_list WHERE inventory_name = ?", (ingredient,))
                inventory_id = cursor.fetchone()
                
                if inventory_id:
                    inventory_id = inventory_id[0]
                    cursor.execute("""
                        INSERT INTO menu_inventory (id, name, inventory_id, inventory_name)
                        VALUES (?, ?, ?, ?)
                    """, (menu_id, drink_name, inventory_id, ingredient))
    conn.commit()
    conn.close()
    print(f"Database initialized and populated with {len(DRINKS_MENU)} drinks!")
    print(f"Database initialized and populated with {len(INVENTORY_LIST)} inventories!")

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

# Run the script
if __name__ == "__main__":
    initialize_database()
