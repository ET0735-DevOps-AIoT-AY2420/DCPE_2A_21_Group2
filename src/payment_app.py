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

# For RFID payment simulation
from rfid_payment import simulate_rfid_payment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration and Setup ---
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "b9faabf6d98e5b9bfc6ccf8f592406c7")
DB_FILE = os.environ.get("DB_PATH", "vending_machine.db")

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

# For RFID payments, a global variable may no longer be needed as the balance is maintained in the database.
# (You can remove the global rfid_balance if all credit deductions are done in the DB.)
rfid_balance = 100.0  # This may be used only for simulation if not stored in the database.

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

@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Handles user and admin login.
    Checks both the 'users' and 'admin_users' tables.
    """
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        logger.info(f"Login attempt - Username: {username}, Password: {password}")

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # Check in 'users' table first
                cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
                user = cursor.fetchone()

                if user:
                    session["user_id"] = user["id"]
                    session["username"] = user["username"]
                    flash("Login successful!", "success")
                    logger.info(f"User login successful: {username}")
                    return redirect(url_for("payment"))

                # If not found, check in 'admin_users' table
                cursor.execute("SELECT * FROM admin_users WHERE username = ? AND password = ?", (username, password))
                admin_user = cursor.fetchone()

                if admin_user:
                    session["user_id"] = admin_user["id"]
                    session["username"] = admin_user["username"]
                    flash("Admin login successful!", "success")
                    logger.info(f"Admin login successful: {username}")
                    return redirect(url_for("payment"))

                # If neither are found, return error
                flash("Invalid username or password", "danger")
                logger.warning(f"Login failed for username: {username}")
                return render_template("index.html")

        except Exception as e:
            logger.error(f"Error during login: {e}")
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

# --- RFID Transaction Functionality ---
def record_rfid_transaction(user_id, item_index, price, rfid_card_id):
    """
    Records an RFID transaction:
      - Deducts the payment amount from the user's credit.
      - Inserts an order record with source 'RFID' and the rfid_card_id.
      - Inserts a corresponding sales record.
    All changes are committed atomically.
    
    Parameters:
      user_id (int): The user's ID.
      item_index (int): Index of the purchased item (0-based).
      price (float): The price of the item.
      rfid_card_id (str): The RFID card identifier.
    """
    current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Deduct the price from the user's credit.
        cursor.execute("UPDATE users SET credit = credit - ? WHERE user_id = ?", (price, user_id))
        
        # Generate a transaction_id using the current timestamp.
        transaction_id = str(datetime.datetime.now().timestamp())
        
        # Insert the RFID transaction into the orders table.
        cursor.execute(
            """
            INSERT INTO orders (item_id, source, status, timestamp, transaction_id, rfid_card_id)
            VALUES (?, 'RFID', 'Completed', ?, ?, ?)
            """,
            (item_index + 1, current_timestamp, transaction_id, rfid_card_id)
        )
        order_id = cursor.lastrowid
        
        # Insert a corresponding record in the sales table.
        cursor.execute(
            """
            INSERT INTO sales (order_id, item_id, timestamp, price, source)
            VALUES (?, ?, ?, ?, 'RFID')
            """,
            (order_id, item_index + 1, current_timestamp, price)
        )
        conn.commit()
        logger.info("RFID transaction recorded: Order ID %s for RFID card %s.", order_id, rfid_card_id)
    except Exception as e:
        conn.rollback()
        logger.error("Error recording RFID transaction: %s", e)
    finally:
        conn.close()

@app.route("/rfid-pay", methods=["POST"])
def rfid_pay():
    """
    Process an RFID payment:
    - Calls simulate_rfid_payment() to wait for a card and process the payment.
    - Updates the user's credit and records the transaction.
    """
    try:
        data = request.get_json()
        item_index = int(data["item_index"])
        selected_item = DRINKS_MENU[item_index]
        price = selected_item["price"]

        # Call the RFID payment simulation (this may block)
        rfid_card_id, new_balance = simulate_rfid_payment(payment_amount=price)
        if not rfid_card_id:
            return jsonify({"error": "RFID payment failed or no card detected."}), 400

        # Record the RFID transaction in the database.
        record_rfid_transaction(user_id=session.get("user_id"),
                                item_index=item_index,
                                price=price,
                                rfid_card_id=rfid_card_id)
        
        return jsonify({"message": "RFID payment successful.", "new_balance": f"{new_balance:.2f}"}), 200
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
            # Check for sufficient credit.
            cursor.execute("SELECT credit FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({"error": "User not found in database."}), 404
            current_credit = row["credit"]
            if current_credit < amount:
                return jsonify({"error": "Insufficient credits for QR payment."}), 400

            # Generate a unique transaction ID and update user credit.
            transaction_id = uuid.uuid4().hex
            new_credit = current_credit - amount
            cursor.execute("UPDATE users SET credit = ? WHERE user_id = ?", (new_credit, user_id))
            conn.commit()

        # Create the QR code payload.
        qr_payload = f"{user_id}:{amount}:{transaction_id}"
        qr_img = qrcode.make(qr_payload)

        # Construct a filename that includes the target Telegram chat ID and transaction ID.
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
                VALUES (?, 'QR', 'Pending', ?, ?)
                """,
                (item_index + 1, current_timestamp, transaction_id)
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
                VALUES (?, 'Stripe', 'Completed', ?)
                """,
                (item_index + 1, current_timestamp)
            )
            order_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO sales (order_id, item_id, timestamp, price, source)
                VALUES (?, ?, ?, ?, 'Stripe')
                """,
                (
                    order_id,
                    item_index + 1,
                    current_timestamp,
                    DRINKS_MENU[item_index]["price"],
                )
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
    app.run(host="0.0.0.0", port=5003, debug=True)
