import pytest
import os
import shutil
from unittest.mock import patch
from flask import session, request
from src.qrcodegen import generate_qr_code  

# Setup and teardown functions
@pytest.fixture(scope="function", autouse=True)
def cleanup_qr_folder():
    """Ensure a clean QR folder before and after tests."""
    qr_folder = "qrcodes"
    if os.path.exists(qr_folder):
        shutil.rmtree(qr_folder)  # Remove any existing QR codes
    os.makedirs(qr_folder, exist_ok=True)
    yield
    shutil.rmtree(qr_folder)  # Clean up after tests

def test_generate_qr_success():
    """Test successful QR code generation."""
    with patch.dict(session, {"user_id": "12345"}), patch.dict(request.form, {"amount": "5.00"}):
        result = generate_qr_code()
        assert "success" in result
        assert os.path.exists(result["file_path"])

def test_generate_qr_missing_user_id():
    """Test failure when user_id is missing."""
    with patch.dict(session, {}, clear=True), patch.dict(request.form, {"amount": "5.00"}):
        result = generate_qr_code()
        assert "error" in result
        assert "Missing user_id" in result["error"]

def test_generate_qr_missing_amount():
    """Test failure when amount is missing."""
    with patch.dict(session, {"user_id": "12345"}), patch.dict(request.form, {}, clear=True):
        result = generate_qr_code()
        assert "error" in result
        assert "Missing user_id or amount" in result["error"]

def test_generate_qr_invalid_amount():
    """Test failure when amount is not a valid number."""
    with patch.dict(session, {"user_id": "12345"}), patch.dict(request.form, {"amount": "invalid"}):
        result = generate_qr_code()
        assert "error" in result
        assert "could not convert string to float" in result["error"]
