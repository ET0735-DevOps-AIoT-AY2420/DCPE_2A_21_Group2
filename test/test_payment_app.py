import pytest
import json
from unittest.mock import patch, MagicMock
from src.payment_app import app, get_db_connection, bot

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client

@patch("src.app.get_db_connection")
def test_login_valid(mock_db, client):
    """Test valid login for both user and admin"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.side_effect = [{"admin_id": 1, "username": "admin"}, None]
    
    response = client.post("/login", data={"username": "admin", "password": "password"}, follow_redirects=True)
    assert b"Admin login successful" in response.data
    
    mock_cursor.fetchone.side_effect = [None, {"user_id": 2, "username": "user"}]
    response = client.post("/login", data={"username": "user", "password": "password"}, follow_redirects=True)
    assert b"User login successful" in response.data

@patch("src.app.get_db_connection")
def test_login_invalid(mock_db, client):
    """Test invalid login credentials"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None
    
    response = client.post("/login", data={"username": "wrong", "password": "wrong"})
    assert b"Invalid username or password" in response.data

@patch("src.app.get_db_connection")
def test_qr_pay(mock_db, client):
    """Test QR payment with sufficient credits"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    
    mock_cursor.fetchone.return_value = {"credit": 10.0}
    mock_cursor.execute.return_value = None
    
    client.post("/login", data={"username": "user", "password": "password"})
    with patch("src.app.qrcode.make"), patch("builtins.open", MagicMock()):
        with patch("src.app.bot.send_photo") as mock_send_photo:
            response = client.post("/qr-pay", json={"item_index": 0})
            mock_send_photo.assert_called_once()
            assert response.status_code == 200
            assert b"QR code generated and sent." in response.data

@patch("src.app.stripe.checkout.Session.create")
def test_create_checkout_session(mock_stripe, client):
    """Test Stripe checkout session creation"""
    mock_stripe.return_value = MagicMock(url="https://stripe.com/test")
    response = client.post("/create-checkout-session", json={"item_index": 0})
    assert response.status_code == 200
    assert b"https://stripe.com/test" in response.data
