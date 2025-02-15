import pytest
import sqlite3
import datetime
import sys
import os 


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from unittest.mock import MagicMock, patch
from src.rfid_payment import get_db_connection, simulate_rfid_payment, record_rfid_transaction

DB_TEST_FILE = ":memory:"  # Use in-memory database for testing

@pytest.fixture
def mock_db_connection():
    """Creates a mock database connection."""
    conn = sqlite3.connect(DB_TEST_FILE)
    conn.execute("CREATE TABLE users (user_id INTEGER PRIMARY KEY, credit REAL)")
    conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, item_id INTEGER, source TEXT, status TEXT, timestamp TEXT, transaction_id TEXT, rfid_card_id TEXT)")
    conn.execute("CREATE TABLE sales (id INTEGER PRIMARY KEY, order_id INTEGER, item_id INTEGER, timestamp TEXT, price REAL, source TEXT)")
    conn.commit()
    yield conn
    conn.close()

@patch("your_module.time.time")
def test_simulate_rfid_payment(mock_time):
    """Tests RFID payment simulation with a mocked time function."""
    start_time = 1000
    mock_time.side_effect = lambda: start_time + (5 if mock_time.call_count >= 5 else mock_time.call_count)
    rfid_card_id, new_balance = simulate_rfid_payment(payment_amount=2.50, timeout=30)
    assert rfid_card_id == "ABC123DEF456"
    assert new_balance == 97.50

@patch("your_module.get_db_connection")
def test_record_rfid_transaction(mock_get_db, mock_db_connection):
    """Tests recording an RFID transaction by checking database inserts."""
    mock_get_db.return_value = mock_db_connection
    mock_cursor = mock_db_connection.cursor()
    
    mock_db_connection.execute("INSERT INTO users (user_id, credit) VALUES (1, 100.0)")
    mock_db_connection.commit()
    
    record_rfid_transaction(user_id=1, price=2.50, rfid_card_id="ABC123DEF456", item_id=1)
    
    cursor = mock_db_connection.cursor()
    cursor.execute("SELECT credit FROM users WHERE user_id = 1")
    new_credit = cursor.fetchone()[0]
    assert new_credit == 97.50
    
    cursor.execute("SELECT COUNT(*) FROM orders")
    assert cursor.fetchone()[0] == 1
    
    cursor.execute("SELECT COUNT(*) FROM sales")
    assert cursor.fetchone()[0] == 1
