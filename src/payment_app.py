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
    # Allow access to the login and static endpoints without login.
    if request.endpoint in ["login", "static"]:
        return
    # If no session exists, redirect to /login
    if "user_id" not in session:
        return redirect("/login")

# --- Root Route ---
@app.route("/")
def home():
    # You may choose to show a home page here; for now we simply redirect to the login page.
    return redirect("/login")

# --- Login Route ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        logger.info(f"Login attempt - Username: '{username}', Password: '{password}'")
        if not username or not password:
            flash("Please enter both username and password", "danger")
            return render_template("index.html")
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Check admin_users table first
                logger.info(f"Checking admin_users table for: Username='{username}', Password='{password}'")
                cursor.execute("SELECT * FROM admin_users WHERE username = ? AND password = ?", (username, password))
                admin_user = cursor.fetchone()
                if admin_user is not None:
                    admin_user = dict(admin_user)
                    session["user_id"] = admin_user["admin_id"]
                    session["username"] = admin_user["username"]
                    flash("Admin login successful!", "success")
                    logger.info(f"Admin login successful: {username}")
                    return redirect(url_for("payment"))
                # Then check users table
                logger.info(f"Checking users table for: Username='{username}', Password='{password}'")
                cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
                user = cursor.fetchone()
                if user is not None:
                    user = dict(user)
                    session["user_id"] = user["user_id"]
                    session["username"] = user["username"]
                    flash("User login successful!", "success")
                    logger.info(f"User login successful: {username}")
                    return redirect(url_for("payment"))
                flash("Invalid username or password", "danger")
                logger.warning(f"Login failed: Invalid credentials for username '{username}'")
                return render_template("index.html")
        except Exception as e:
            logger.error(f"Error during login: {e}")
            flash("An error occurred. Please try again.", "danger")
            return render_template("index.html")
    return render_template("index.html")

# --- Logout Route ---
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# --- Payment Route ---
@app.route("/payment")
def payment():
    return render_template("payment.html", drinks=DRINKS_MENU)

# --- Stripe Payment Route ---
@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    try:
        data = request.get_json()
        item_index = int(data["item_index"])
        selected_item = DRINKS_MENU[item_index]
        price_in_cents = int(selected_item["price"] * 100)
        session_stripe = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": selected_item["name"]},
                    "unit_amount": price_in_cents,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=url_for("success", item_index=item_index, _external=True),
            cancel_url=url_for("cancel", _external=True),
        )
        return jsonify({"url": session_stripe.url})
    except Exception as e:
        logger.error("Stripe session creation error: %s", e)
        return jsonify({"error": str(e)}), 400

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
        
        # Return a JSON response with a redirect URL so that client-side JS can redirect
        return jsonify({"redirect": url_for("success", item_index=item_index)})
        
    except Exception as e:
        logger.error("Error in RFID payment: %s", e)
        flash("Error processing RFID payment.", "danger")
        return jsonify({"error": "Error processing RFID payment."})

# --- QR Payment Route ---
@app.route("/qr-pay", methods=["POST"])
def qr_pay():
    try:
        data = request.get_json()
        item_index = int(data["item_index"])
        selected_item = DRINKS_MENU[item_index]
        amount = selected_item["price"]
        user_id = session.get("user_id")
        if user_id is None:
            return jsonify({"error": "User not logged in."}), 401
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT credit FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({"error": "User not found in database."}), 404
            current_credit = row["credit"]
            if current_credit < amount:
                return jsonify({"error": "Insufficient credits for QR payment."}), 400
            transaction_id = uuid.uuid4().hex
            new_credit = current_credit - amount
            cursor.execute("UPDATE users SET credit = ? WHERE user_id = ?", (new_credit, user_id))
            conn.commit()
        qr_payload = f"{user_id}:{amount}:{transaction_id}"
        qr_img = qrcode.make(qr_payload)
        filename = f"qr_{TELEGRAM_CHAT_ID}_{transaction_id}.png"
        file_path = os.path.join(QR_FOLDER, filename)
        qr_img.save(file_path)
        logger.info("QR code saved to %s", file_path)
        current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO orders (item_id, source, status, timestamp, transaction_id)
                VALUES (?, 'QR', 'Pending', ?, ?)
                """,
                (item_index + 1, current_timestamp, transaction_id)
            )
            conn.commit()
        return jsonify({"message": "QR code generated and queued for sending via Telegram."})
    except Exception as e:
        logger.error("Error in QR payment: %s", e)
        return jsonify({"error": str(e)}), 500

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

# --- Cancel Route ---
@app.route("/cancel")
def cancel():
    return "Payment canceled"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
