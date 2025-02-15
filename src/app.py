import os
import sqlite3
import stripe
import uuid
import io
import qrcode
import threading
import pytz
from datetime import datetime
#from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
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

from hal import hal_lcd as LCD


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Import RFID functions from rfid_payment.py
from rfid_payment import simulate_rfid_payment, record_rfid_transaction

app = Flask(__name__, template_folder="templates")
app.secret_key = "b9faabf6d98e5b9bfc6ccf8f592406c7"  # For testing purposes

CORS(app)

DB_FILE = os.getenv("DB_PATH", "/data/vending_machine.db")

# Stripe configuration
stripe.api_key = "sk_test_51Qh9kW06aB8tsnc6hM4v2C48GHGTHJEhDr6iqSw471hz1UmloXMf3wq88Qw2vC1HzIgOEHTOlxfFPnromgpf964R00vHQZySAx"

# Telegram Bot configuration
TELEGRAM_BOT_TOKEN = "7722732406:AAFEAXz_RTJNRAnE9aRnOVtlN18G7V-0wWU"
TELEGRAM_CHAT_ID = "1498916836"
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Drinks menu data with images
DRINKS_MENU = [
    # Hot Beverages
    {"name": "Classic Coffee", "category": "Hot Beverage", "price": 2.50, "availability": True, "image": "classic_coffee.jpg"},
    {"name": "Strawberry Latte", "category": "Hot Beverage", "price": 3.00, "availability": True, "image": "strawberry_latte.jpg"},
    {"name": "Lychee Milk Tea", "category": "Hot Beverage", "price": 3.50, "availability": True, "image": "lychee_milk_tea.jpg"},
    {"name": "Mocha Strawberry Twist", "category": "Hot Beverage", "price": 4.00, "availability": True, "image": "mocha_strawberry_twist.jpg"},
    {"name": "Lime Infused Coffee", "category": "Hot Beverage", "price": 2.75, "availability": True, "image": "lime_infused_coffee.jpg"},

    # Cold Beverages
    {"name": "Iced Coffee", "category": "Cold Beverage", "price": 3.00, "availability": True, "image": "iced_coffee.jpg"},
    {"name": "Strawberry Iced Latte", "category": "Cold Beverage", "price": 3.50, "availability": True, "image": "strawberry_iced_latte.jpg"},
    {"name": "Lychee Cooler", "category": "Cold Beverage", "price": 3.75, "availability": True, "image": "lychee_cooler.jpg"},
    {"name": "Lime Lychee Refresher", "category": "Cold Beverage", "price": 3.25, "availability": True, "image": "lime_lychee_refresher.jpg"},
    {"name": "Coffee Berry Chill", "category": "Cold Beverage", "price": 4.50, "availability": True, "image": "coffee_berry_chill.jpg"},

    # Soda Mixes
    {"name": "Strawberry Soda Fizz", "category": "Soda Mix", "price": 3.00, "availability": True, "image": "strawberry_soda_fizz.jpg"},
    {"name": "Lime Sparkle", "category": "Soda Mix", "price": 3.00, "availability": True, "image": "lime_sparkle.jpg"},
    {"name": "Lychee Lime Spritz", "category": "Soda Mix", "price": 3.50, "availability": True, "image": "lychee_lime_spritz.jpg"},
    {"name": "Coffee Soda Kick", "category": "Soda Mix", "price": 4.00, "availability": True, "image": "coffee_soda_kick.jpg"},
    {"name": "Strawberry Lychee Sparkler", "category": "Soda Mix", "price": 4.25, "availability": True, "image": "strawberry_lychee_sparkler.jpg"},

    # Smoothies
    {"name": "Strawberry Milk Smoothie", "category": "Smoothie", "price": 3.50, "availability": True, "image": "strawberry_milk_smoothie.jpg"},
    {"name": "Lychee Delight Smoothie", "category": "Smoothie", "price": 3.75, "availability": True, "image": "lychee_delight_smoothie.jpg"},
    {"name": "Tropical Lime Smoothie", "category": "Smoothie", "price": 4.00, "availability": True, "image": "tropical_lime_smoothie.jpg"},
    {"name": "Strawberry Coffee Smoothie", "category": "Smoothie", "price": 4.50, "availability": True, "image": "strawberry_coffee_smoothie.jpg"},
    {"name": "Lychee Strawberry Frost", "category": "Smoothie", "price": 4.25, "availability": True, "image": "lychee_strawberry_frost.jpg"},
]


# Define Singapore Time Zone
SGT = pytz.timezone('Asia/Singapore')

# Function to Get Current Time in Singapore Time
def get_sg_time():
    return datetime.now(SGT).strftime('%Y-%m-%d %H:%M:%S')

# Function to Get Database Connection
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Enables access to columns by name
    return conn

# --- Setup QR Codes Folder ---
QR_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qrcodes")
os.makedirs(QR_FOLDER, exist_ok=True)

# Route to Render Menu Page
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/payment')
def payment_page():
    order_id = request.args.get("order_id")
    item_index = request.args.get("item_index")
    return render_template("payment.html", order_id=order_id, item_index=item_index)

# Fetch Menu
@app.route('/menu', methods=['GET'])
def get_menu():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT m.id, m.name, m.category, m.price, m.image, 
            CASE 
                WHEN EXISTS (
                    SELECT 1 FROM menu_inventory mi 
                    JOIN inventory_list il ON mi.inventory_id = il.inventory_id 
                    WHERE mi.id = m.id AND il.amount <= 0
                ) 
                THEN 0 ELSE m.availability 
            END AS availability
        FROM menu m
    """)

    drinks = cursor.fetchall()
    conn.close()

    menu = [
        {
            "id": d["id"],
            "name": d["name"],
            "category": d["category"],
            "price": d["price"],
            "available": bool(d["availability"]),
            "image": d["image"]
        }
        for d in drinks
    ]
    return jsonify(menu)

#Route for Order Page
@app.route('/order/<int:drink_id>', methods=['GET'])
def order_page(drink_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, image FROM menu WHERE id = ?", (drink_id,))
    drink = cursor.fetchone()
    conn.close()

    if not drink:
        return "Drink not found", 404

    return render_template("order.html", drink=drink)

#check phone number 
@app.route("/check-phone-number", methods=["POST"])
def check_phone_number():
    try:
        data = request.get_json()
        phone_number = data.get("phone_number")

        if not phone_number:
            return jsonify({"error": "Phone number is required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT chat_id FROM users WHERE phone_number = ?", (phone_number,))
        user = cursor.fetchone()
        conn.close()

        if user:
            return jsonify({"exists": True})
        else:
            return jsonify({"exists": False})

    except Exception as e:
        logger.error("Error checking phone number: %s", e)
        return jsonify({"error": "Server error"}), 500


# Place Order
@app.route("/order", methods=["POST"])
def place_order():
    try:
        data = request.get_json()

        # Validate required fields
        if "item_index" not in data or "phone_number" not in data:
            return jsonify({"error": "Missing item_index or phone_number"}), 400

        item_index = int(data["item_index"])
        phone_number = data["phone_number"]

        # 🔍 Retrieve user_id using phone_number
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE phone_number = ?", (phone_number,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found"}), 404

        user_id = user["user_id"]

        # 🔍 Get item details
        if item_index < 0 or item_index >= len(DRINKS_MENU):
            return jsonify({"error": "Invalid item index"}), 400

        selected_item = DRINKS_MENU[item_index]
        price = selected_item["price"]

        # ✅ Insert into orders table
        current_timestamp = get_sg_time()
        cursor.execute("""
            INSERT INTO orders (item_id, user_id, source, status, timestamp)
            VALUES (?, ?, 'remote', 'Pending', ?)
        """, (item_index + 1, user_id, current_timestamp))
        order_id = cursor.lastrowid

        conn.commit()
        conn.close()

        # ✅ Return a POST request payload
        return jsonify({
            "order_id": order_id,
            "item_index": item_index
        })

    except Exception as e:
        logger.error("Error in placing order: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/orders', methods=['GET'])
def get_orders():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch only paid orders
    cursor.execute("SELECT order_id, item_id FROM orders WHERE status='Paid' AND source='remote' ORDER BY order_id ASC")
    orders = [{"order_id": row[0], "item_id": row[1]} for row in cursor.fetchall()]
    
    conn.close()
    return jsonify(orders)

# Create Stripe Checkout Session
@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    try:
        data = request.get_json()

        # Validate required fields
        if "item_index" not in data or "order_id" not in data:
            return jsonify({"error": "Missing order_id or item_index"}), 400

        item_index = int(data["item_index"])
        order_id = int(data["order_id"])

        # Validate item index
        if item_index < 0 or item_index >= len(DRINKS_MENU):
            return jsonify({"error": "Invalid item index"}), 400

        selected_item = DRINKS_MENU[item_index]
        price_in_cents = int(selected_item["price"] * 100)

        # Create Stripe Checkout Session
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
            success_url=url_for("success", order_id=order_id, item_index=item_index, _external=True),
            cancel_url=url_for("cancel", _external=True),
        )

        return jsonify({"url": session_stripe.url})

    except Exception as e:
        logger.error("Stripe session creation error: %s", e)
        return jsonify({"error": str(e)}), 400


@app.route("/success")
def success():
    try:
        order_id = request.args.get("order_id")
        
        if not order_id:
            return jsonify({"error": "Order ID is required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 🔍 Get item_id & user_id from orders
        cursor.execute("SELECT item_id, user_id, source FROM orders WHERE order_id=?", (order_id,))
        order = cursor.fetchone()

        if not order:
            return jsonify({"error": "Order not found"}), 404

        item_id, user_id, order_source = order["item_id"], order["user_id"], order["source"]

        # 🔍 Get price from menu
        cursor.execute("SELECT price FROM menu WHERE id=?", (item_id,))
        menu_item = cursor.fetchone()

        if not menu_item:
            return jsonify({"error": "Item not found in menu"}), 404

        price = menu_item["price"]
        current_timestamp = get_sg_time()

        # 🔍 Get user credit balance and chat_id
        cursor.execute("SELECT credit, chat_id, phone_number FROM users WHERE user_id=?", (user_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found"}), 404

        current_credit, chat_id, phone_number = user["credit"], user["chat_id"], user["phone_number"]

        # ❗ Check if user has enough credit
        if current_credit < price:
            return jsonify({"error": "Insufficient credit."}), 400

        # ✅ Deduct credit from user's balance
        new_credit = current_credit - price
        cursor.execute("UPDATE users SET credit = ? WHERE user_id = ?", (new_credit, user_id))

        # ✅ Update order status to 'Paid'
        cursor.execute("UPDATE orders SET status='Paid' WHERE order_id=?", (order_id,))

        # ✅ Insert into sales table
        cursor.execute("""
            INSERT INTO sales (order_id, item_id, timestamp, price, source, payment_source)
            VALUES (?, ?, ?, ?, ?, 'Card')
        """, (order_id, item_id, current_timestamp, price, order_source))

        # ✅ Generate & Send QR Code for drink collection
        transaction_id = uuid.uuid4().hex
        qr_payload = f"{user_id}:{order_id}:{transaction_id}"
        qr_img = qrcode.make(qr_payload)
        filename = f"qr_{chat_id}_{transaction_id}.png"
        file_path = os.path.join(QR_FOLDER, filename)
        qr_img.save(file_path)

        logger.info("QR code saved to %s", file_path)

        # ✅ Insert QR code into `collection_qr_codes` table for tracking
        cursor.execute("""
            INSERT INTO collection_qr_codes (order_id, phone_number, chat_id, qr_code, status, timestamp)
            VALUES (?, ?, ?, ?, 'Pending', ?)
        """, (order_id, phone_number, chat_id, transaction_id, current_timestamp))

        # ✅ Send QR code image to Telegram
        with open(file_path, "rb") as f:
            bot.send_photo(chat_id=chat_id, photo=f)
            bot.send_message(chat_id=chat_id, text=f"✅ QR code for order {order_id} generated. Use this QR code to collect your drink.")

        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    except Exception as e:
        logger.error("Error in success route: %s", e)
        return jsonify({"error": str(e)}), 500

# Cancel Payment
@app.route('/cancel')
def cancel():
    return "Payment was cancelled. You can try again.", 200

@app.route("/qr-pay", methods=["POST"])
def qr_pay():
    try:
        data = request.get_json()
        item_index = int(data["item_index"])
        order_id = data.get("order_id")
        phone_number = data.get("phone_number")

        if not phone_number:
            return jsonify({"error": "Phone number is required"}), 400

        if not order_id:
            logger.error("❌ Missing order_id in /qr-pay request!")
            return jsonify({"error": "Order ID is required for QR payment."}), 400

        logger.info(f"✅ Received order_id: {order_id}, phone_number: {phone_number}")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Retrieve the chat_id associated with the phone number
        cursor.execute("SELECT chat_id, credit FROM users WHERE phone_number = ?", (phone_number,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "Phone number not found in database."}), 404

        chat_id = user["chat_id"]
        current_credit = user["credit"]
        selected_item = DRINKS_MENU[item_index]
        amount = selected_item["price"]

        if current_credit < amount:
            return jsonify({"error": "Insufficient credits for QR payment."}), 400

        # Generate transaction ID
        transaction_id = uuid.uuid4().hex
        new_credit = current_credit - amount

        # Deduct balance & log transaction
        cursor.execute("UPDATE users SET credit = ? WHERE phone_number = ?", (new_credit, phone_number))

        # ✅ Update the orders table with `payment_source`, `transaction_id`
        cursor.execute("""
            UPDATE orders 
            SET transaction_id = ?, payment_source = 'QR' 
            WHERE order_id = ?
        """, (transaction_id, order_id))

        # ✅ Insert into the `qr_transactions` table
        cursor.execute("""
            INSERT INTO qr_transactions (transaction_id, order_id, phone_number, status) 
            VALUES (?, ?, ?, 'Pending')
        """, (transaction_id, order_id, phone_number))

        conn.commit()

        # Generate the QR payload and create the QR code image
        qr_payload = f"{phone_number}:{amount}:{transaction_id}"
        qr_img = qrcode.make(qr_payload)
        filename = f"qr_{chat_id}_{transaction_id}.png"
        file_path = os.path.join(QR_FOLDER, filename)
        qr_img.save(file_path)

        logger.info("✅ QR code saved to %s", file_path)

        # Send QR code image to Telegram
        with open(file_path, "rb") as f:
            bot.send_photo(chat_id=chat_id, photo=f)
            bot.send_message(chat_id=chat_id, text=f"✅ QR code for transaction {transaction_id} generated. Amount: {amount}")

        logger.info(f"✅ Successfully updated order {order_id} with transaction ID {transaction_id}")

        return jsonify({
            "message": "QR code generated and sent successfully.",
            "transaction_id": transaction_id
        })

    except Exception as e:
        logger.error("❌ Error in QR payment: %s", e)
        return jsonify({"error": str(e)}), 500

# Check Inventory Status
def check_inventory_status(drink_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT amount FROM inventory_list 
        WHERE inventory_id IN (SELECT inventory_id FROM menu_inventory WHERE id = ?)
    """, (drink_id,))
    result = cursor.fetchone()
    conn.close()

    return result and result["amount"] > 0

# Run Flask only if executed directly
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
