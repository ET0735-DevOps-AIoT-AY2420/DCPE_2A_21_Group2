import stripe
import sqlite3
import RPi.GPIO as GPIO
from flask import Flask, request, render_template, jsonify
import time
import atexit

# Import the HAL file for RFID support
from hal.hal_rfid_reader import SimpleMFRC522

app = Flask(__name__)
DB_FILE = "vending_machine.db"

# Initialize RFID Reader from HAL
reader = SimpleMFRC522()

# GPIO Setup (Avoids Conflicts)
GPIO.setwarnings(False)
if GPIO.getmode() is None:
    GPIO.setmode(GPIO.BCM)

# Vending Machine Relay GPIO Pin
VENDING_RELAY_PIN = 17
GPIO.setup(VENDING_RELAY_PIN, GPIO.OUT)

# Ensure GPIO cleanup on exit
atexit.register(GPIO.cleanup)

# Stripe API Key
stripe.api_key = "sk_test_51Qh9kW06aB8tsnc6hM4v2C48GHGTHJEhDr6iqSw471hz1UmloXMf3wq88Qw2vC1HzIgOEHTOlxfFPnromgpf964R00vHQZySAx"

# Drinks Menu
DRINKS_MENU = [
    {"name": "Classic Coffee", "price": 2.50},
    {"name": "Strawberry Latte", "price": 3.00},
    {"name": "Lychee Milk Tea", "price": 3.50},
    {"name": "Mocha Strawberry Twist", "price": 4.00},
    {"name": "Lime Infused Coffee", "price": 2.75},
]

def get_db_connection():
    return sqlite3.connect(DB_FILE)

# Function to trigger vending mechanism
def dispense_drink():
    print("Dispensing drink...")
    GPIO.output(VENDING_RELAY_PIN, GPIO.HIGH)
    time.sleep(2)
    GPIO.output(VENDING_RELAY_PIN, GPIO.LOW)
    print("Drink dispensed.")

# Route: RFID Payment
@app.route("/rfid-pay", methods=["POST"])
def rfid_pay():
    try:
        print("Waiting for RFID scan...")
        uid, text = reader.read()  # Read RFID tag
        print(f"RFID Tag Detected: {uid}")

        data = request.get_json()
        item_index = int(data["item_index"])

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, price FROM menu WHERE id = ?", (item_index + 1,))
        item = cursor.fetchone()

        if not item:
            return jsonify({"error": "Invalid item selection"}), 400

        item_id, price = item

        cursor.execute("SELECT balance FROM rfid_users WHERE rfid_tag_id = ?", (str(uid),))
        user = cursor.fetchone()

        if user:
            balance = user[0]
            if balance >= price:
                new_balance = balance - price
                cursor.execute("UPDATE rfid_users SET balance = ? WHERE rfid_tag_id = ?", (new_balance, str(uid)))
                cursor.execute("INSERT INTO sales (item_id, price, source) VALUES (?, ?, ?)", (item_id, price, "RFID"))
                conn.commit()

                dispense_drink()

                return jsonify({"message": "Payment successful", "new_balance": new_balance}), 200
            else:
                return jsonify({"error": "Insufficient balance. Please reload."}), 400
        else:
            return jsonify({"error": "Card not registered"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()

# Route: Reload RFID Balance
@app.route("/rfid-reload", methods=["POST"])
def rfid_reload():
    try:
        uid, text = reader.read()  # Read RFID tag
        data = request.get_json()
        amount = float(data["amount"])

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM rfid_users WHERE rfid_tag_id = ?", (str(uid),))
        user = cursor.fetchone()

        if user:
            new_balance = user[0] + amount
            cursor.execute("UPDATE rfid_users SET balance = ? WHERE rfid_tag_id = ?", (new_balance, str(uid)))
            conn.commit()
            return jsonify({"message": f"Balance reloaded. New balance: ${new_balance}"}), 200
        else:
            cursor.execute("INSERT INTO rfid_users (rfid_tag_id, username, balance) VALUES (?, ?, ?)", (str(uid), "New User", amount))
            conn.commit()
            return jsonify({"message": f"New RFID card registered with balance: ${amount}"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()

if __name__ == "__main__":
    app.run(debug=True)
