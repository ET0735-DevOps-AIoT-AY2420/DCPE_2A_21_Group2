import time
from datetime import datetime
from threading import Thread
import queue
import pytz
import sqlite3
import prepare
import requests

# Importing hardware abstraction libraries (HALs)
from hal import hal_led as led
from hal import hal_lcd as LCD
from hal import hal_adc as adc
from hal import hal_buzzer as buzzer
from hal import hal_keypad as keypad
from hal import hal_moisture_sensor as moisture_sensor
from hal import hal_input_switch as input_switch
from hal import hal_ir_sensor as ir_sensor
from hal import hal_rfid_reader as rfid_reader
from hal import hal_servo as servo
from hal import hal_temp_humidity_sensor as temp_humid_sensor
from hal import hal_usonic as usonic
from hal import hal_dc_motor as dc_motor
from hal import hal_accelerometer as accel

# Queue for storing keypad inputs
shared_keypad_queue = queue.Queue()

# Database file location
DB_FILE = "vending_machine.db"

# Define Singapore Time Zone
SGT = pytz.timezone('Asia/Singapore')

# Function to Get Current Time in Singapore Time
def get_sg_time():
    return datetime.now(SGT).strftime('%Y-%m-%d %H:%M:%S')

#function to check inventory before confirming order
def check_inventory_status(drink_id):
    """

    Checks if there is enough inventory for the selected drink.

    Args:
        drink_id (int)

    Returns:
        bool: True if there is enough inventory, False otherwie.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("SELECT inventory_id FROM menu_inventory WHERE id = ?", (drink_id,))
        inventory_ids = cursor.fetchall()

        #No inventory linked to drink
        if not inventory_ids:
            print(f" [ERROR] No inventory found for Drink ID {drink_id}.")
            conn.close()
            return False
        
        #Check inventory level for each required inventory
        for inventory_id in inventory_ids:
            cursor.execute("SELECT inventory_name, amount FROM inventory_list WHERE inventory_id = ?", (inventory_id[0],))
            result = cursor.fetchone()

            #inventory item is missing
            if result is None:
                print(f"[ERROR] Inventory ID {inventory_id[0]} not found in inventory_list.")
                return False
            
            inventory_name, amount = result
            
            if amount < 2:
                print(f"[ERROR] Not enough inventory for {inventory_name} (only{amount} left).")
                conn.close()
                return False
            
            print(f" [DEBUG] Inventory for {inventory_name} is available: {amount} units.")

        conn.close()
        return True # inventory is sufficient
    
    except Exception as e:
        print(f" [ERROR] Database error: {e}")
        return False
    
    finally:
        conn.close()

# Buffer for handling multi-digit keypad inputs
input_buffer = ""
awaiting_multi_digit_input = False

# Callback function for handling keypress events from the keypad
def key_pressed(key):
    """
    Handles keypress events and manages input buffer for multi-digit inputs.
    """
    global input_buffer, awaiting_multi_digit_input
    if awaiting_multi_digit_input and key in range(10):  # If awaiting input, add digits to buffer
        input_buffer += str(key)
    elif awaiting_multi_digit_input and key == "#":  # Confirm multi-digit input with '#'
        if input_buffer:  # Add to queue only if input exists
            shared_keypad_queue.put(input_buffer)
            input_buffer = ""
    elif awaiting_multi_digit_input and key == "*":  # Clear buffer on '*'
        input_buffer = ""
    elif not awaiting_multi_digit_input and key in range(10):  # Directly handle single-digit inputs
        shared_keypad_queue.put(str(key))

# Fetch available menu items from the database
def fetch_menu():
    """
    Retrieves all available menu items (availability = 1) from the database.
    Returns:
        list: A list of tuples containing item ID, name, price, and availability.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, availability FROM menu WHERE availability = 1")
    menu = cursor.fetchall()
    conn.close()
    return menu

# Insert a new order into the database
def insert_order(item_id, source):
    """
    Inserts a new order into the database.
    Args:
        item_id (int): ID of the selected menu item.
        source (str): Source of the order (e.g., "local").
    Returns:
        int: The order ID of the newly created order.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (item_id, source, status, timestamp) VALUES (?, 'local', 'Pending', ?)", 
               (item_id, get_sg_time()))
    conn.commit()
    order_id = cursor.lastrowid  # Get the ID of the inserted order
    conn.close()
    return order_id

# Update the status of an order in the database
def update_order_status(order_id, status):
    """
    Updates the status of a specific order in the database.
    Args:
        order_id (int): ID of the order.
        status (str): New status (e.g., "Completed", "Preparing").
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = ? WHERE order_id = ?", (status, order_id))
    conn.commit()
    conn.close()

# Fetch next order (Local & Remote)
def fetch_next_order():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Fetch remote orders
        response = requests.get("http://localhost:5000/order")
        if response.status_code == 200:
            remote_orders = response.json()
            for order in remote_orders:
                order_id = order["order_id"]
                item_id = order["item_id"]

                # Check if already in SQLite
                cursor.execute("SELECT order_id FROM orders WHERE order_id = ?", (order_id,))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO orders (order_id, item_id, source, status) VALUES (?, ?, 'remote', 'Pending')", (order_id, item_id))
                    conn.commit()
                    print(f"[DEBUG] Inserted Remote Order {order_id}")

        # Fetch oldest pending order
        cursor.execute("SELECT order_id, item_id, source FROM orders WHERE status = 'Pending' ORDER BY timestamp LIMIT 1")
        next_order = cursor.fetchone()
        conn.close()

        return next_order if next_order else None

    except Exception as e:
        print(f"[ERROR] fetch_next_order failed: {e}")
        return None


# Generate initials for drink names
def get_initials(name):
    """
    Creates initials from a drink's name (e.g., "Classic Coffee" -> "CC").
    Args:
        name (str): The name of the drink.
    Returns:
        str: The initials of the drink name.
    """
    words = name.split()
    initials = ''.join(word[0].upper() for word in words)
    return initials

def main():
    """
    Main function to handle the vending machine's operations.
    """
    global input_buffer, awaiting_multi_digit_input

    # Initialize hardware modules
    led.init()
    adc.init()
    buzzer.init()
    moisture_sensor.init()
    input_switch.init()
    ir_sensor.init()
    reader = rfid_reader.init()
    servo.init()
    temp_humid_sensor.init()
    usonic.init()
    dc_motor.init()
    accelerometer = accel.init()

    # Initialize keypad and start a thread for key detection
    keypad.init(key_pressed)
    keypad_thread = Thread(target=keypad.get_key)
    keypad_thread.start()

    # Initialize LCD display
    lcd = LCD.lcd()
    lcd.lcd_clear()

    lcd.lcd_display_string("Smart Vending", 1)
    lcd.lcd_display_string("System Ready", 2)
    time.sleep(3)

    while True:
        # Continuously check and process any pending orders first (Remote or Local)
        while True:
            next_order = fetch_next_order()
            if next_order:
                order_id, item_id, source = next_order  # Fetch the source (local/remote)

                lcd.lcd_clear()
                lcd.lcd_display_string(f"Preparing #{item_id}", 1)
                update_order_status(order_id, "Preparing")

                if prepare.prepare_drink(item_id):
                    update_order_status(order_id, "Completed")
                    lcd.lcd_clear()
                    lcd.lcd_display_string("Drink Ready!", 1)
                else:
                    update_order_status(order_id, "Failed")
                    lcd.lcd_clear()
                    lcd.lcd_display_string("Prep Failed", 1)
                time.sleep(3)
            else:
                break  # No more pending orders, proceed to local order input

        # Now, wait for a local order, but continue checking for remote orders
        lcd.lcd_clear()
        lcd.lcd_display_string("Enter Item #", 1)

        # Display menu on the terminal and LCD
        menu = fetch_menu()
        for item in menu:
            print(f"{item[0]}. {item[1]} - ${item[2]:.2f}")

        # Wait for keypad input but check for remote orders periodically
        input_buffer = ""
        awaiting_multi_digit_input = True
        while not shared_keypad_queue.qsize():
            lcd.lcd_display_string(f"Input: {input_buffer[:16]}{' ' * (16 - len(input_buffer))}", 2)
            time.sleep(0.1)

            # While waiting, check for new remote orders
            next_order = fetch_next_order()
            if next_order:
                break  # Immediately process new order

        # If a new remote order was found, process it before accepting local input
        if next_order:
            continue  # Go back to the top of the loop to process the pending order

        keyvalue = shared_keypad_queue.get()
        awaiting_multi_digit_input = False

        try:
            item_id = int(keyvalue)
            if any(item[0] == item_id for item in menu):  # Validate item ID
                selected_item = next(item for item in menu if item[0] == item_id)
                initials = get_initials(selected_item[1])

                # Check inventory before confirmation
                print(f" Checking inventory for Drink #{item_id}...")
                if not check_inventory_status(item_id):
                    print(f" [ERROR] Not enough stock for Drink #{item_id}.")
                    lcd.lcd_clear()
                    lcd.lcd_display_string("Not enough stock", 1)
                    time.sleep(2)
                    continue  # Skip the rest of the loop and go back to drink selection

                # Display selected drink details
                lcd.lcd_clear()
                lcd.lcd_display_string(f"Selected: {initials}", 1)
                lcd.lcd_display_string(f"Price: ${selected_item[2]:.2f}", 2)
                buzzer.beep(0.2, 0.1, 1)
                time.sleep(2)

                # Confirm order
                lcd.lcd_clear()
                lcd.lcd_display_string("Confirm?", 1)
                lcd.lcd_display_string("1-Yes 2-No", 2)
                confirm_key = shared_keypad_queue.get()
                buzzer.beep(0.1, 0.1, 1)

                if confirm_key == "1":  # User confirms the order
                    order_id = insert_order(item_id, "local")
                    lcd.lcd_clear()
                    lcd.lcd_display_string(f"Preparing #{item_id}", 1)

                    # Call the preparation function
                    if prepare.prepare_drink(item_id):
                        update_order_status(order_id, "Completed")
                        lcd.lcd_clear()
                        lcd.lcd_display_string("Drink Ready!", 1)
                    else:
                        update_order_status(order_id, "Failed")
                        lcd.lcd_clear()
                        lcd.lcd_display_string("Prep Failed", 1)
                    time.sleep(2)
                elif confirm_key == "2":
                    lcd.lcd_clear()
                    lcd.lcd_display_string("Cancelled", 1)
                    time.sleep(2)
            else:
                lcd.lcd_clear()
                lcd.lcd_display_string("Invalid Item", 1)
                buzzer.beep(0.2, 0.1, 2)
                time.sleep(2)
        except ValueError:
            lcd.lcd_clear()
            lcd.lcd_display_string("Invalid Input", 1)
            buzzer.beep(0.2, 0.1, 2)
            time.sleep(2)

if __name__ == "__main__":
    main()
