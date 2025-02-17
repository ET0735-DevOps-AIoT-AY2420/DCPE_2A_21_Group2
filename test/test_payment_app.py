import os
import sqlite3
import pytest
from datetime import datetime
import pytz
from unittest.mock import patch
from pathlib import Path

# Import functions and the bot instance from main.py.
from main import (
    get_sg_time,
    get_initials,
    get_user_id,
    insert_order,
    update_order_status,
    check_inventory_status,
    send_telegram_message,
    DB_FILE,
    bot
)

# ------------------------------------------------------------------
# Fixture: Use a temporary file-based SQLite database for testing.
# ------------------------------------------------------------------
@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    # Create a temporary file for the database.
    db_file = tmp_path / "test_vending_machine.db"
    # Override the environment variable and module-level DB_FILE so that
    # get_db_connection() uses our temporary database.
    monkeypatch.setenv("DB_PATH", str(db_file))
    monkeypatch.setattr("main.DB_FILE", str(db_file))
    
    # Create the database and required tables.
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create minimal tables required for testing.
    cursor.execute("""
    CREATE TABLE users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone_number TEXT UNIQUE,
        chat_id TEXT,
        credit REAL
    )
    """)
    
    cursor.execute("""
    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER,
        user_id INTEGER,
        source TEXT,
        status TEXT,
        timestamp TEXT,
        payment_source TEXT,
        transaction_id TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE menu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL,
        availability INTEGER,
        image TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE inventory_list (
        inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
        inventory_name TEXT,
        amount INTEGER
    )
    """)
    
    cursor.execute("""
    CREATE TABLE menu_inventory (
        id INTEGER,
        name TEXT,
        inventory_id INTEGER,
        inventory_name TEXT
    )
    """)
    
    # Insert a dummy menu item (id = 1)
    cursor.execute("""
    INSERT INTO menu (name, price, availability, image)
    VALUES ('Test Drink', 2.50, 1, 'test_drink.jpg')
    """)
    
    conn.commit()
    yield conn  # Provide the connection for testing.
    conn.close()

# -------------------------------------------------
# Test get_sg_time() – Check time format
# -------------------------------------------------
def test_get_sg_time():
    sg_time = get_sg_time()
    try:
        datetime.strptime(sg_time, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        pytest.fail("get_sg_time() does not return time in the correct format.")

# -------------------------------------------------
# Test get_initials() – Generate initials from drink name
# -------------------------------------------------
def test_get_initials():
    assert get_initials("Classic Coffee") == "CC"
    assert get_initials("Strawberry Latte") == "SL"
    assert get_initials("Lychee Milk Tea") == "LMT"

# -------------------------------------------------
# Test get_user_id() – Retrieve user by phone number
# -------------------------------------------------
def test_get_user_id(temp_db):
    conn = temp_db
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (phone_number, chat_id, credit) VALUES (?, ?, ?)",
                   ("1234567890", "test_chat", 50.0))
    conn.commit()
    user_id = cursor.lastrowid

    returned_user_id = get_user_id("1234567890")
    assert returned_user_id == user_id, f"Expected {user_id}, got {returned_user_id}"
    assert get_user_id("0000000000") is None

# -------------------------------------------------
# Test insert_order() and update_order_status()
# -------------------------------------------------
def test_insert_and_update_order(temp_db):
    conn = temp_db
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (phone_number, chat_id, credit) VALUES (?, ?, ?)",
                   ("1234567890", "test_chat", 100.0))
    user_id = cursor.lastrowid
    conn.commit()

    order_id = insert_order(0, user_id, "local", "RFID")
    assert order_id is not None

    update_order_status(order_id, "Completed")
    
    new_conn = sqlite3.connect(os.getenv("DB_PATH"))
    new_conn.row_factory = sqlite3.Row
    new_cursor = new_conn.cursor()
    new_cursor.execute("SELECT status FROM orders WHERE order_id = ?", (order_id,))
    row = new_cursor.fetchone()
    new_conn.close()
    assert row is not None
    assert row["status"] == "Completed"

# -------------------------------------------------
# Test send_telegram_message() using monkeypatch and direct _dict_ update
# -------------------------------------------------
def test_send_telegram_message(temp_db):
    calls = []
    def fake_send_message(chat_id, text):
        calls.append((chat_id, text))
    # Directly update bot._dict_ to override the frozen send_message method.
    bot._dict_["send_message"] = fake_send_message

    send_telegram_message("Test alert")
    # Note: The actual chat id in main.py is 5819192033.
    assert calls == [(5819192033, "Test alert")]

# -------------------------------------------------
# Test check_inventory_status() – Inventory sufficiency check
# -------------------------------------------------
def test_check_inventory_status(temp_db):
    conn = temp_db
    cursor = conn.cursor()
    cursor.execute("INSERT INTO inventory_list (inventory_name, amount) VALUES (?, ?)", ("water", 5))
    inventory_id = cursor.lastrowid
    cursor.execute("INSERT INTO menu_inventory (id, name, inventory_id, inventory_name) VALUES (?, ?, ?, ?)",
                   (1, "Test Drink", inventory_id, "water"))
    conn.commit()
    
    status = check_inventory_status(1)
    assert status is True

    cursor.execute("UPDATE inventory_list SET amount = ? WHERE inventory_id = ?", (1, inventory_id))
    conn.commit()
    status = check_inventory_status(1)
    assert status is False