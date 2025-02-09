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
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Get Pending Orders
    cursor.execute("SELECT * FROM orders WHERE status = 'Pending'")
    pending_orders = cursor.fetchall()

    # Get All-time Sales
    cursor.execute("SELECT SUM(price) FROM sales")
    total_sales = cursor.fetchone()[0]

    # Get Inventory
    cursor.execute("SELECT inventory_name, amount FROM inventory_list")
    inventory = cursor.fetchall()

    conn.close()

    return render_template('admin_dashboard.html', pending_orders=pending_orders, total_sales=total_sales, inventory=inventory)


# Modify Drink Details
@app.route('/modify_drink/<int:drink_id>', methods=['GET', 'POST'])
def modify_drink(drink_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if request.method == 'POST':
        new_price = request.form['price']
        availability = request.form['availability']
        
        cursor.execute(""" 
            UPDATE menu
            SET price = ?, availability = ?
            WHERE id = ?
        """, (new_price, availability, drink_id))
        
        conn.commit()
        flash("Drink details updated successfully.")
        return redirect(url_for('admin_dashboard'))
    
    cursor.execute("SELECT * FROM menu WHERE id = ?", (drink_id,))
    drink = cursor.fetchone()
    conn.close()
    
    return render_template('modify_drink.html', drink=drink)


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


# Logout Admin
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin_login'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)  # Admin Panel runs on port 5002
