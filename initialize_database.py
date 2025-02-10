import os
import sqlite3
import bcrypt
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_FILE = os.environ.get("DB_FILE", "vending_machine.db")

DRINKS_MENU = [
    {
        "name": "Classic Coffee",
        "category": "Hot Beverage",
        "price": 2.50,
        "availability": True,
        "image": "classic_coffee.jpg",
    },
    {
        "name": "Strawberry Latte",
        "category": "Hot Beverage",
        "price": 3.00,
        "availability": True,
        "image": "strawberry_latte.jpg",
    },
    {
        "name": "Lychee Milk Tea",
        "category": "Hot Beverage",
        "price": 3.50,
        "availability": True,
        "image": "lychee_milk_tea.jpg",
    },
    {
        "name": "Mocha Strawberry Twist",
        "category": "Hot Beverage",
        "price": 4.00,
        "availability": True,
        "image": "mocha_strawberry_twist.jpg",
    },
    {
        "name": "Lime Infused Coffee",
        "category": "Hot Beverage",
        "price": 2.75,
        "availability": True,
        "image": "lime_infused_coffee.jpg",
    },
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
    {"inventory_name": "soda", "amount": 10},
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
}

def initialize_database():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            # Enable foreign keys in SQLite
            conn.execute("PRAGMA foreign_keys = ON;")
            cursor = conn.cursor()

            # Create the users table if it doesn't exist
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users';"
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    """
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password BLOB NOT NULL,
                        credit REAL NOT NULL DEFAULT 0.0,
                        telegram_started INTEGER DEFAULT 0
                    )
                    """
                )
                logger.info("Created users table.")
            else:
                cursor.execute("PRAGMA table_info(users);")
                columns = [col_info[1] for col_info in cursor.fetchall()]
                if "credit" not in columns:
                    cursor.execute(
                        "ALTER TABLE users ADD COLUMN credit REAL NOT NULL DEFAULT 0.0;"
                    )
                    logger.info("Added credit column to users table.")

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS menu (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    price REAL NOT NULL,
                    availability BOOLEAN NOT NULL,
                    image TEXT
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Pending',
                    timestamp TEXT NOT NULL,
                    transaction_id TEXT,
                    FOREIGN KEY (item_id) REFERENCES menu (id)
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sales (
                    sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    item_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    price REAL NOT NULL,
                    source TEXT NOT NULL,
                    FOREIGN KEY (item_id) REFERENCES menu (id),
                    FOREIGN KEY (order_id) REFERENCES orders (order_id)
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS inventory_list (
                    inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inventory_name TEXT NOT NULL,
                    amount INTEGER NOT NULL
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS menu_inventory (
                    id INTEGER,
                    name TEXT,
                    inventory_id INTEGER,
                    inventory_name TEXT,
                    FOREIGN KEY(id) REFERENCES menu(id),
                    FOREIGN KEY(inventory_id) REFERENCES inventory_list(inventory_id)
                )
                """
            )

            # Insert test user if not already present
            cursor.execute("SELECT id FROM users WHERE username = ?", ("test_user",))
            if cursor.fetchone() is None:
                hashed_password = bcrypt.hashpw("password123".encode("utf-8"), bcrypt.gensalt())
                cursor.execute(
                    """
                    INSERT INTO users (username, password, credit)
                    VALUES (?, ?, ?)
                    """,
                    ("test_user", hashed_password, 100.0),
                )
                logger.info("Inserted test_user into the database.")
            else:
                logger.info("test_user already exists. Skipping insertion.")

            # Optionally populate menu and inventory_list tables here.
            # For example, to insert drinks into the menu table:
            # for drink in DRINKS_MENU:
            #     cursor.execute(
            #         "INSERT OR IGNORE INTO menu (name, category, price, availability, image) VALUES (?, ?, ?, ?, ?)",
            #         (drink["name"], drink["category"], drink["price"], drink["availability"], drink["image"]),
            #     )
            conn.commit()
            logger.info("Database initialized and populated with data!")
    except Exception as e:
        logger.error("Error initializing database: %s", e)

if __name__ == "__main__":
    initialize_database()
