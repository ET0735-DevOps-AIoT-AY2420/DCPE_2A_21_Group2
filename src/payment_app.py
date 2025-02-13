#!/usr/bin/env python3
import os
import stripe
import sqlite3
import datetime
import uuid
import io
import qrcode
import time
import threading
from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
    jsonify,
    session,
    flash,
    Response  # Keep Response for potential future use
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

# --- Flask App Configuration ---
app = Flask(__name__)
app.secret_key = "b9faabf6d98e5b9bfc6ccf8f592406c7"  # For testing purposes

# Database file path
DB_FILE = "/home/pi/Jaeson/vending_machine.db"

# Stripe configuration
stripe.api_key = "sk_test_51Qh9kW06aB8tsnc6hM4v2C48GHGTHJEhDr6iqSw471hz1UmloXMf3wq88Qw2vC1HzIgOEHTOlxfFPnromgpf964R00vHQZySAx"

# Telegram Bot configuration
TELEGRAM_BOT_TOKEN = "7854261569:AAHLf1DASQHn1MBiryaxGuEcaJtephX8d7M"
TELEGRAM_CHAT_ID = "871756841"
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Sample drinks menu
DRINKS_MENU = [
    {"name": "Classic Coffee", "category": "Hot Beverage", "price": 2.50, "availability": True, "image": "classic_coffee.jpg"},
    {"name": "Strawberry Latte", "category": "Hot Beverage", "price": 3.00, "availability": True, "image": "strawberry_latte.jpg"},
    {"name": "Lychee Milk Tea", "category": "Hot Beverage", "price": 3.50, "availability": True, "image": "lychee_milk_tea.jpg"},
    {"name": "Mocha Strawberry Twist", "category": "Hot Beverage", "price": 4.00, "availability": True, "image": "mocha_strawberry_twist.jpg"},
    {"name": "Lime Infused Coffee", "category": "Hot Beverage", "price": 2.75, "availability": True, "image": "lime_infused_coffee.jpg"},
]

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- Setup QR Codes Folder ---
QR_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qrcodes")
os.makedirs(QR_FOLDER, exist_ok=True)

# --- Flask Routes ---
@app.before_request
def require_login():
    if request.endpoint in ["login", "static"]:
        return
    if "user_id" not in session:
        return redirect("/login")

@app.route("/")
def home():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        logger.info(f"Login attempt - Username: '{username}'")
        if not username or not password:
            flash("Please enter both username and password", "danger")
            return render_template("index.html")
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM admin_users WHERE username = ? AND password = ?", (username, password))
                admin_user = cursor.fetchone()
                if admin_user is not None:
                    admin_user = dict(admin_user)
                    session["user_id"] = admin_user["admin_id"]
                    session["username"] = admin_user["username"]
                    flash("Admin login successful!", "success")
                    return redirect(url_for("payment"))
                cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
                user = cursor.fetchone()
                if user is not None:
                    user = dict(user)
                    session["user_id"] = user["user_id"]
                    session["username"] = user["username"]
                    flash("User login successful!", "success")
                    return redirect(url_for("payment"))
                flash("Invalid username or password", "danger")
                return render_template("index.html")
        except Exception as e:
            logger.error(f"Error during login: {e}")
            flash("An error occurred. Please try again.", "danger")
            return render_template("index.html")
    return render_template("index.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/payment")
def payment():
    return render_template("payment.html", drinks=DRINKS_MENU)

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
        led.set_output(0, 1)
        
        # Wait for RFID card scan (up to 30 seconds)
        rfid_card_id, new_balance = simulate_rfid_payment(payment_amount=price, timeout=30)
        led.set_output(0, 0)
        
        if not rfid_card_id:
            lcd.lcd_clear()
            lcd.lcd_display_string("Scan Timed Out", 1)
            flash("RFID payment timed out.", "danger")
            return render_template("payment.html", drinks=DRINKS_MENU)

        logger.info(f"Recording RFID transaction: user_id={session.get('user_id')}, price={price}, rfid_card_id={rfid_card_id}, item_id={item_index + 1}")
        record_rfid_transaction(
            user_id=session.get("user_id"),
            price=price,
            rfid_card_id=rfid_card_id,
            item_id=item_index + 1
        )
        lcd.lcd_clear()
        lcd.lcd_display_string("Payment Successful", 1)
        time.sleep(2)
        
        return jsonify({"redirect": url_for("success", item_index=item_index)})
    except Exception as e:
        logger.error("Error in RFID payment: %s", e)
        flash("Error processing RFID payment.", "danger")
        return jsonify({"error": "Error processing RFID payment."})

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

        # Generate the QR payload and create the QR code image.
        qr_payload = f"{user_id}:{amount}:{transaction_id}"
        qr_img = qrcode.make(qr_payload)
        filename = f"qr_{TELEGRAM_CHAT_ID}_{transaction_id}.png"
        file_path = os.path.join(QR_FOLDER, filename)
        qr_img.save(file_path)
        logger.info("QR code saved to %s", file_path)

        # Send QR code image to Telegram.
        with open(file_path, "rb") as f:
            bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=f)
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"QR code for transaction {transaction_id} generated.  Amount: {amount}")


        current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO orders (item_id, source, status, timestamp, transaction_id)
                VALUES (?, 'QR', 'Paid', ?, ?)
                """,  # Change status directly to 'Paid'
                (item_index + 1, current_timestamp, transaction_id)
            )
            conn.commit()

        return jsonify({"message": "QR code generated and sent.", "redirect": url_for("success", item_index=item_index,_external=True)})

    except Exception as e:
        logger.error("Error in QR payment: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route("/success")
def success():
    try:
        item_index = request.args.get("item_index", default=0, type=int)
        selected_item = DRINKS_MENU[item_index]

        # Initialize LCD
        lcd = LCD.lcd()
        lcd.lcd_clear()

        # Display "Payment Complete" message and flash
        for _ in range(3):  # Flash 3 times
            lcd.lcd_display_string("Payment Complete", 1)
            time.sleep(0.3)
            lcd.lcd_clear()
            time.sleep(0.3)
        lcd.lcd_display_string("Payment Complete", 1) # show the string after flashing
        time.sleep(2) # keep the final message for 2 seconds before returning to payment page
        lcd.lcd_clear()

        return render_template("success.html", item=selected_item)
    except Exception as e:
        logger.error("Error in success route: %s", e)
        return f"Error processing payment: {e}", 500

@app.route("/cancel")
def cancel():
    return "Payment canceled"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)