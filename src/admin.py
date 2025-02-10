from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import pytz
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this for security

# Define database file
DB_FILE = "vending_machine.db"

# Define Singapore Time
SGT = pytz.timezone('Asia/Singapore')

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
        cursor.execute("SELECT id FROM admin_users WHERE username = ? AND password = ?", (username, password))
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

    # Get Pending Orders
    cursor.execute("""
        SELECT orders.order_id, orders.item_id, menu.name, orders.status
        FROM orders
        JOIN menu ON orders.item_id = menu.id
        WHERE orders.status = 'Pending'
    """)
    pending_orders = cursor.fetchall()

    # Get Sales data
    date_filter = request.form.get('date_filter', 'all')  # default to all time
    if date_filter == 'daily':
        cursor.execute("SELECT SUM(price) FROM sales WHERE timestamp >= date('now', 'localtime')")
    elif date_filter == 'weekly':
        cursor.execute("SELECT SUM(price) FROM sales WHERE timestamp >= date('now', '-7 days')")
    elif date_filter == 'monthly':
        cursor.execute("SELECT SUM(price) FROM sales WHERE timestamp >= date('now', '-30 days')")
    else:  # all time
        cursor.execute("SELECT SUM(price) FROM sales")

    total_sales = cursor.fetchone()[0] or 0  # If no sales, set to 0

    # Get Inventory
    cursor.execute("SELECT inventory_name, amount FROM inventory_list")
    inventory = cursor.fetchall()

    conn.close()

    return render_template('admin_dashboard.html', pending_orders=pending_orders, total_sales=total_sales, inventory=inventory)


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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)  # Admin Panel runs on port 5002
