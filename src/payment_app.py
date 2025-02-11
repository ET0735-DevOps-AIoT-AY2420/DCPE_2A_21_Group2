#!/usr/bin/env python3
import os
import stripe
import sqlite3
import datetime
import uuid
import io
import qrcode
import time
from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
    jsonify,
    session,
    flash,
)
from telegram import Bot
import bcrypt
import logging

# Import RFID functions from rfid_payment.py
from rfid_payment import simulate_rfid_payment, record_rfid_transaction

# Import LCD and LED functions from your HAL module
from hal import hal_lcd as LCD
from hal import hal_led as led

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration and Setup ---
app = Flask(__name__)
app.secret_key = "b9faabf6d98e5b9bfc6ccf8f592406c7"  # For testing purposes

# Set the database file path
DB_FILE = "/home/pi/Jaeson/vending_machine.db"

# Stripe configuration (for card payments)
stripe.api_key = "sk_test_51Qh9kW06aB8tsnc6hM4v2C48GHGTHJEhDr6iqSw471hz1UmloXMf3wq88Qw2vC1HzIgOEHTOlxfFPnromgpf964R00vHQZySAx"

# Telegram Bot configuration
TELEGRAM_BOT_TOKEN = "7854261569:AAHLf1DASQHn1MBiryaxGuEcaJtephX8d7M"
TELEGRAM_CHAT_ID = "871756841"
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Sample drinks menu – must match the data in your database
DRINKS_MENU = [
    {"name": "Classic Coffee", "category": "Hot Beverage", "price": 2.50, "availability": True, "image": "classic_coffee.jpg"},
    {"name": "Strawberry Latte", "category": "Hot Beverage", "price": 3.00, "availability": True, "image": "strawberry_latte.jpg"},
    {"name": "Lychee Milk Tea", "category": "Hot Beverage", "price": 3.50, "availability": True, "image": "lychee_milk_tea.jpg"},
    {"name": "Mocha Strawberry Twist", "category": "Hot Beverage", "price": 4.00, "availability": True, "image": "mocha_strawberry_twist.jpg"},
    {"name": "Lime Infused Coffee", "category": "Hot Beverage", "price": 2.75, "availability": True, "image": "lime_infused_coffee.jpg"},
]

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Enable dictionary-style access
    return conn

# --- Setup QR Codes Folder ---
QR_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qrcodes")
os.makedirs(QR_FOLDER, exist_ok=True)

# --- Before Request: Require Login for Protected Endpoints ---
@app.before_request
def require_login():
    if request.endpoint not in ["login", "home", "static"] and "user_id" not in session:
        return redirect(url_for("login"))

# --- Payment (Ordering) Route ---
@app.route("/payment")
def payment():
    return render_template("payment.html", drinks=DRINKS_MENU)

# --- RFID Payment Route with LCD and LED Feedback ---
@app.route("/rfid-pay", methods=["POST"])
def rfid_pay():
    try:
        data = request.get_json()
        item_index = int(data["item_index"])
        selected_item = DRINKS_MENU[item_index]
        price = selected_item["price"]
        
        # Initialize LCD and LED for feedback
        lcd = LCD.lcd()
        led.init()
        lcd.lcd_clear()
        lcd.lcd_display_string("Tap your card here!", 1)
        led.set_output(0, 1)  # Turn LED on (indicating ready to scan)
        
        # Wait for RFID card scan (up to 30 seconds)
        rfid_card_id, new_balance = simulate_rfid_payment(payment_amount=price, timeout=30)
        
        # Turn LED off after scanning
        led.set_output(0, 0)
        
        if not rfid_card_id:
            lcd.lcd_clear()
            lcd.lcd_display_string("Scan Timed Out", 1)
            flash("RFID payment timed out.", "danger")
            return render_template("payment.html", drinks=DRINKS_MENU)

        # Log RFID transaction attempt
        logger.info(f"Recording RFID transaction: user_id={session.get('user_id')}, price={price}, rfid_card_id={rfid_card_id}, item_id={item_index + 1}")

        # Record the RFID transaction in the database.
        record_rfid_transaction(
            user_id=session.get("user_id"),
            price=price,
            rfid_card_id=rfid_card_id,
            item_id=item_index + 1
        )
        
        # Update LCD to indicate success
        lcd.lcd_clear()
        lcd.lcd_display_string("Payment Successful", 1)
        time.sleep(2)

        # Redirect to success page
        return jsonify({"redirect": url_for("success", item_index=item_index)})

    except Exception as e:
        logger.error("Error in RFID payment: %s", e)
        flash("Error processing RFID payment.", "danger")
        return jsonify({"error": "Error processing RFID payment."})

# --- Success Route ---
@app.route("/success")
def success():
    try:
        item_index = request.args.get("item_index", default=0, type=int)
        selected_item = DRINKS_MENU[item_index]
        return render_template("success.html", item=selected_item)
    except Exception as e:
        logger.error("Error in success route: %s", e)
        return f"Error processing payment: {e}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
