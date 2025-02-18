import os
import sqlite3
import pytz
import threading
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from time import sleep
import RPi.GPIO as GPIO
from telegram import Bot
from hal import hal_moisture_sensor as moisture
from hal import hal_led as LED
from hal import dht11 as DHT11

# Global variables to track previous states
previous_moisture_state = None
previous_temperature = None

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this for security

# Define database file
DB_FILE = os.getenv("DB_PATH", "/data/vending_machine.db")

# Define Singapore Time
SGT = pytz.timezone('Asia/Singapore')

# Define DHT11 sensor pin
DHT_PIN = 21
dht11_sensor = DHT11.DHT11(pin=DHT_PIN)

# Initialize hardware modules
moisture.init()
LED.init()

# Telegram Bot Configuration
BOT_TOKEN = "7722732406:AAFEAXz_RTJNRAnE9aRnOVtlN18G7V-0wWU"
CHAT_ID = "1498916836"
bot = Bot(token=BOT_TOKEN)

# Function to send Telegram alerts
def send_telegram_message(message):
    def send():
        try:
            bot.send_message(chat_id=CHAT_ID, text=message)
        except Exception as e:
            print(f"Error sending Telegram message: {e}")
    # Run in a new thread so it doesn't block execution
    threading.Thread(target=send, daemon=True).start()

# Function to check moisture sensor
def moisture_status():
    global previous_moisture_state
    moisture_level = moisture.read_sensor()

    if moisture_level and previous_moisture_state != moisture_level:
        previous_moisture_state = moisture_level  # Update state
        LED.set_output(24, GPIO.HIGH)
        send_telegram_message("Water leakage detected. Technician access needed!")
    elif not moisture_level and previous_moisture_state != moisture_level:
        previous_moisture_state = moisture_level  # Update state
        LED.set_output(24, GPIO.LOW)

def temp_and_humidity():
    global previous_temperature
    result = dht11_sensor.read()

    if result.is_valid():
        temperature = result.temperature
        humidity = result.humidity

        print(f"[DEBUG] Temp: {temperature}, Humidity: {humidity}")  # Debugging line

        # Only send a message if the temperature crosses a threshold
        if previous_temperature is None or abs(previous_temperature - temperature) >= 1:
            previous_temperature = temperature  # Update state
            if temperature < 25 or temperature > 30:
                LED.set_output(24, GPIO.HIGH)
                print("[DEBUG] Sending alert: Temperature out of range!")  # Debugging line
                send_telegram_message(
                    f"Temperature: {temperature}°C\n"
                    f"Humidity: {humidity}%\n"
                    "Temperature is out of range. Technician access needed!"
                )
            else:
                LED.set_output(24, GPIO.LOW)

# Background function to monitor sensors continuously
def monitor_sensors():
    while True:
        print("[DEBUG] Monitoring sensors...")  # Add this
        moisture_status()
        temp_and_humidity()
        sleep(10)


def start_sensor_monitoring():
    if hasattr(app, 'sensor_monitoring_started') and app.sensor_monitoring_started:
        print("[DEBUG] Sensor monitoring is already running.")
        return

    print("[DEBUG] Starting sensor monitoring in background...")
    sensor_thread = threading.Thread(target=monitor_sensors, daemon=True)
    sensor_thread.start()
    app.sensor_monitoring_started = True  # Set flag to prevent multiple starts

    
# Function to get Singapore time
def get_sg_time():
    return datetime.now(SGT).strftime('%Y-%m-%d %H:%M:%S')

# Route to Render Menu Page
@app.route('/')
def index():
    return render_template("admin_login.html")

# Admin Login Page
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if admin exists with the given username and password
        cursor.execute("SELECT admin_id FROM admin_users WHERE username = ? AND password = ?", (username, password))
        admin = cursor.fetchone()

        if admin:
            # Store admin in session and log the login activity
            session['admin_id'] = admin[0]
            log_ip_address(admin[0], request.remote_addr)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password')
        
        conn.close()
    
    return render_template('admin_login.html')


# Admin Dashboard
@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # ✅ Get filter values
    date_filter = request.form.get('date_filter', 'all')  # Default: all time
    source_filter = request.form.get('source_filter', 'all')  # Default: all sources

    # ✅ Base SQL query
    query = """
    SELECT sales.sale_id, sales.order_id, menu.name, sales.timestamp, sales.price, sales.source, sales.payment_source
    FROM sales
    JOIN menu ON sales.item_id = menu.id
    WHERE 1=1  -- Placeholder for dynamic filters
    """

    # ✅ Add source filter dynamically
    if source_filter == "local":
        query += " AND sales.source = 'local'"
    elif source_filter == "remote":
        query += " AND sales.source = 'remote'"

    # ✅ Add date filter dynamically
    if date_filter == 'daily':
        query += " AND sales.timestamp >= date('now', 'localtime')"
    elif date_filter == 'weekly':
        query += " AND sales.timestamp >= date('now', '-7 days')"
    elif date_filter == 'monthly':
        query += " AND sales.timestamp >= date('now', '-30 days')"

    query += " ORDER BY sales.timestamp DESC"

    # ✅ Execute the query
    cursor.execute(query)
    sales_data = cursor.fetchall()

    # ✅ Get Total Sales Based on Filter
    total_query = "SELECT SUM(price) FROM sales WHERE 1=1"

    if source_filter == "local":
        total_query += " AND sales.source = 'local'"
    elif source_filter == "remote":
        total_query += " AND sales.source = 'remote'"

    if date_filter == 'daily':
        total_query += " AND timestamp >= date('now', 'localtime')"
    elif date_filter == 'weekly':
        total_query += " AND timestamp >= date('now', '-7 days')"
    elif date_filter == 'monthly':
        total_query += " AND timestamp >= date('now', '-30 days')"

    cursor.execute(total_query)
    total_sales = cursor.fetchone()[0] or 0  # If no sales, set to 0

    # ✅ Get Inventory
    cursor.execute("SELECT inventory_name, amount FROM inventory_list")
    inventory = cursor.fetchall()

    conn.close()

    return render_template(
        'admin_dashboard.html',
        sales_data=sales_data,
        total_sales=total_sales,
        inventory=inventory,
        selected_date_filter=date_filter,
        selected_source_filter=source_filter
    )

# Modify Inventory Details
@app.route('/modify_inventory/<inventory_name>', methods=['GET', 'POST'])
def modify_inventory(inventory_name):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if request.method == 'POST':
        new_amount = request.form['amount']
        cursor.execute("UPDATE inventory_list SET amount = ? WHERE inventory_name = ?", (new_amount, inventory_name))
        conn.commit()
        flash("Inventory updated successfully.")
        return redirect(url_for('admin_dashboard'))

    cursor.execute("SELECT * FROM inventory_list WHERE inventory_name = ?", (inventory_name,))
    inventory_item = cursor.fetchone()  # Fetch a single record

    if inventory_item is None:
        flash("Inventory item not found!", "error")
        return redirect(url_for('admin_dashboard'))  # Redirect if item is missing

    conn.close()

    return render_template('modify_inventory.html', inventory_item=inventory_item)

# Log IP Address for Admin Login
def log_ip_address(admin_id, ip_address):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO admin_logs (admin_id, ip_address, timestamp)
        VALUES (?, ?, ?)
    """, (admin_id, ip_address, get_sg_time()))
    conn.commit()
    conn.close()

@app.route('/inventory_list')
def inventory_list():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT inventory_name FROM inventory_list")
    inventory = cursor.fetchall()
    conn.close()

    return render_template('inventory_list.html', inventory=inventory)


# Admin Logs Page
@app.route('/admin_logs')
def admin_logs():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT admin_id, ip_address, timestamp FROM admin_logs ORDER BY timestamp DESC")
    logs = cursor.fetchall()
    conn.close()

    return render_template('admin_logs.html', logs=logs)

# Logout Admin
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin_login'))

@app.before_request
def before_request():
    if not hasattr(app, 'sensor_monitoring_started'):
        start_sensor_monitoring()
        app.sensor_monitoring_started = True  # Prevent multiple executions


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)  # Admin Panel runs on port 5002
