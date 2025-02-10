import os
import stripe
import sqlite3
import datetime
import uuid
import io
import qrcode
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration and Setup ---
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "b9faabf6d98e5b9bfc6ccf8f592406c7")
DB_FILE = os.environ.get("DB_FILE", "vending_machine.db")

# Stripe configuration (for card payments)
stripe.api_key = os.environ.get(
    "STRIPE_API_KEY",
    "sk_test_51Qh9kW06aB8tsnc6hM4v2C48GHGTHJEhDr6iqSw471hz1UmloXMf3wq88Qw2vC1HzIgOEHTOlxfFPnromgpf964R00vHQZySAx",
)

# Telegram Bot configuration
TELEGRAM_BOT_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN", "7854261569:AAHLf1DASQHn1MBiryaxGuEcaJtephX8d7M"
)
# Use a fixed Telegram chat ID for now.
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "871756841")
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# For RFID payments, consider storing the balance in the database.
rfid_balance = 100.0

# Sample drinks menu (should match your database/menu)
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

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- Setup QR Codes Folder ---
# Define the folder where QR codes will be stored.
QR_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qrcodes")
os.makedirs(QR_FOLDER, exist_ok=True)

# --- Before Request: Require Login for Protected Endpoints ---
@app.before_request
def require_login():
    if request.endpoint not in ["login", "home", "static"] and "user_id" not in session:
        return redirect(url_for("login"))

# --- Root Route ---
@app.route("/")
def home():
    return render_template("index.html")

# --- User Login Routes ---
@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Handles user login.
    """
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                user = cursor.fetchone()
            if user and bcrypt.checkpw(password.encode("utf-8"), user["password"]):
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                return redirect(url_for("payment"))
            else:
                flash("Invalid username or password", "danger")
                return render_template("index.html")
        except Exception as e:
            logger.error("Error during login: %s", e)
            flash("An error occurred. Please try again.", "danger")
            return render_template("index.html")
    return render_template("index.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# --- Payment (Ordering) Routes ---
@app.route("/payment")
def payment():
    return render_template("payment.html", drinks=DRINKS_MENU)

@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    """Process a card payment via Stripe."""
    try:
        data = request.get_json()
        item_index = int(data["item_index"])
        selected_item = DRINKS_MENU[item_index]
        price_in_cents = int(selected_item["price"] * 100)
        session_stripe = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": selected_item["name"]},
                        "unit_amount": price_in_cents,
                    },
                    "quantity": 1,
                }
            ],
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
    """Simulate RFID payment by deducting from a global balance."""
    global rfid_balance
    try:
        data = request.get_json()
        item_index = int(data["item_index"])
        selected_item = DRINKS_MENU[item_index]
        price = selected_item["price"]
        if rfid_balance < price:
            return jsonify({"error": "Insufficient RFID credit."}), 400
        rfid_balance -= price
        current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO orders (item_id, source, status, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (item_index + 1, "RFID", "Completed", current_timestamp),
            )
            order_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO sales (order_id, item_id, timestamp, price, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                (order_id, item_index + 1, current_timestamp, price, "RFID"),
            )
            conn.commit()
        return jsonify(
            {"message": "RFID payment successful.", "new_balance": f"{rfid_balance:.2f}"}
        ), 200
    except Exception as e:
        logger.error("Error in RFID payment: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route("/qr-pay", methods=["POST"])
def qr_pay():
    """
    Generate a QR code containing (user_id:amount:transaction_id),
    save it to a local folder, and record a pending order.
    The Telegram bot will later detect the file and send it.
    """
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
            # Only check for sufficient credit.
            cursor.execute("SELECT credit FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({"error": "User not found in database."}), 404
            current_credit = row["credit"]
            if current_credit < amount:
                return jsonify({"error": "Insufficient credits for QR payment."}), 400

            # Generate a unique transaction ID and update user credit.
            transaction_id = uuid.uuid4().hex
            new_credit = current_credit - amount
            cursor.execute("UPDATE users SET credit = ? WHERE id = ?", (new_credit, user_id))
            conn.commit()

        # Create the QR code payload.
        qr_payload = f"{user_id}:{amount}:{transaction_id}"
        qr_img = qrcode.make(qr_payload)

        # Construct a filename that includes the target Telegram chat ID and transaction ID.
        # Example filename: "qr_871756841_<transaction_id>.png"
        filename = f"qr_{TELEGRAM_CHAT_ID}_{transaction_id}.png"
        file_path = os.path.join(QR_FOLDER, filename)
        qr_img.save(file_path)
        logger.info("QR code saved to %s", file_path)

        # (Optional) Record a pending order in the database with the transaction ID.
        current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO orders (item_id, source, status, timestamp, transaction_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (item_index + 1, "QR", "Pending", current_timestamp, transaction_id),
            )
            conn.commit()

        return jsonify({"message": "QR code generated and queued for sending via Telegram."})
    except Exception as e:
        logger.error("Error in QR payment: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route("/success")
def success():
    """
    Called after a successful Stripe payment.
    Records the order and sale.
    """
    try:
        item_index = request.args.get("item_index", default=0, type=int)
        selected_item = DRINKS_MENU[item_index]
        current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO orders (item_id, source, status, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (item_index + 1, "Stripe", "Completed", current_timestamp),
            )
            order_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO sales (order_id, item_id, timestamp, price, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    item_index + 1,
                    current_timestamp,
                    DRINKS_MENU[item_index]["price"],
                    "Stripe",
                ),
            )
            conn.commit()
        return render_template("success.html", item=selected_item)
    except Exception as e:
        logger.error("Error in success route: %s", e)
        return f"Error processing payment: {e}", 500

@app.route("/cancel")
def cancel():
    return "Payment canceled"

if __name__ == "__main__":
    app.run(debug=True, port=5003)

