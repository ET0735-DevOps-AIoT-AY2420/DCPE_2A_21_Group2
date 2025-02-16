import os
import sqlite3
from datetime import datetime, timedelta
import random
import pytz

# Database file
DB_FILE = os.getenv("DB_PATH", "/data/vending_machine.db")

# Define Singapore Time
SGT = pytz.timezone('Asia/Singapore')

# Function to get Singapore time
def get_sg_time():
    return datetime.now(SGT).strftime('%Y-%m-%d %H:%M:%S')

# Function to generate random date within the past 3 months
def random_date_within_three_months():
    today = datetime.today()
    start_date = today - timedelta(days=90)  # 90 days ago
    random_days = random.randint(0, 90)
    random_date = start_date + timedelta(days=random_days)
    return random_date.strftime('%Y-%m-%d %H:%M:%S')

# Function to insert random orders and sales
def generate_orders_and_sales():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Get the menu items
    cursor.execute("SELECT id FROM menu")
    menu_items = cursor.fetchall()
    if not menu_items:
        print("No menu items found in the database.")
        return

    # Get user IDs
    cursor.execute("SELECT user_id FROM users")
    user_ids = [row[0] for row in cursor.fetchall()]
    if not user_ids:
        print("No users found in the database.")
        return

    # Generate random orders and sales
    for _ in range(100):  # Insert 100 random orders (adjust this number as needed)
        drink_id = random.choice(menu_items)[0]
        user_id = random.choice(user_ids)
        order_timestamp = random_date_within_three_months()
        source = random.choice(["local", "remote"])  # Randomly choose 'local' or 'remote'
        payment_source = random.choice(["Card", "QR", "RFID"])  # Randomly assign payment source

        # Insert into orders table
        cursor.execute("""
            INSERT INTO orders (item_id, user_id, source, payment_source, status, timestamp)
            VALUES (?, ?, ?, ?, 'Completed', ?)
        """, (drink_id, user_id, source, payment_source, order_timestamp))
        order_id = cursor.lastrowid

        # Generate a sale based on this order
        sale_timestamp = order_timestamp  # Same timestamp for sale
        price = cursor.execute("SELECT price FROM menu WHERE id = ?", (drink_id,)).fetchone()[0]

        cursor.execute("""
            INSERT INTO sales (order_id, item_id, timestamp, price, source, payment_source)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (order_id, drink_id, sale_timestamp, price, source, payment_source))

    conn.commit()
    conn.close()
    print("Successfully generated 100 random orders and sales.")

# Run the data generation
if __name__ == "__main__":
    generate_orders_and_sales()
