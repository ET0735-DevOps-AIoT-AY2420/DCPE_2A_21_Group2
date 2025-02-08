import sqlite3
import pytz
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__, template_folder="templates")
CORS(app)

DB_FILE = "vending_machine.db"

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

# Route to Render Menu Page
@app.route('/')
def index():
    return render_template("menu.html")

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


# Place Order
@app.route('/order', methods=['POST'])
def place_order():
    data = request.json
    drink_id = data.get('drink_id')

    if not check_inventory_status(drink_id):
        return jsonify({"status": "error", "message": "Out of Stock"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (item_id, source, status, timestamp) VALUES (?, 'remote', 'Pending', ?)", 
               (drink_id, get_sg_time()))
    conn.commit()
    order_id = cursor.lastrowid
    conn.close()

    return jsonify({"status": "success", "order_id": order_id, "message": "Order Placed"}), 201

# Fetch Pending Remote Orders
@app.route('/orders', methods=['GET'])
def get_orders():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT order_id, item_id FROM orders WHERE status='Pending' AND source='remote' ORDER BY order_id ASC")
    orders = [{"order_id": row[0], "item_id": row[1]} for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(orders)

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
