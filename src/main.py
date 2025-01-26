import time
from threading import Thread
import queue
import sqlite3

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

# Empty list to store sequence of keypad presses
shared_keypad_queue = queue.Queue()

# Database file
DB_FILE = "vending_machine.db"

# Buffer for multiple-digit keypad inputs
input_buffer = ""
awaiting_multi_digit_input = False

# Callback function invoked when any key on keypad is pressed
def key_pressed(key):
    global input_buffer, awaiting_multi_digit_input
    if awaiting_multi_digit_input and key in range(10):  # Handle digits during multi-digit input
        input_buffer += str(key)
    elif awaiting_multi_digit_input and key == "#":  # Confirm multi-digit input
        if input_buffer:  # Only put in the queue if there's input
            shared_keypad_queue.put(input_buffer)
            input_buffer = ""
    elif awaiting_multi_digit_input and key == "*":  # Clear multi-digit input
        input_buffer = ""
    elif not awaiting_multi_digit_input and key in range(10):  # Directly handle single-digit inputs
        shared_keypad_queue.put(str(key))

# Fetch menu from database
def fetch_menu():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, availability FROM menu WHERE availability = 1")
    menu = cursor.fetchall()
    conn.close()
    return menu

# Insert new order into database
def insert_order(item_id, source):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (item_id, source) VALUES (?, ?)", (item_id, source))
    conn.commit()
    conn.close()

# Update order status in database
def update_order_status(order_id, status):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = ? WHERE order_id = ?", (status, order_id))
    conn.commit()
    conn.close()

# Fetch the next pending order
def fetch_next_order():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT order_id, item_id FROM orders WHERE status = 'Pending' ORDER BY timestamp LIMIT 1")
    order = cursor.fetchone()
    conn.close()
    return order

# Generate initials for drink name
def get_initials(name):
    words = name.split()
    initials = ''.join(word[0].upper() for word in words)
    return initials

def main():
    global input_buffer, awaiting_multi_digit_input
    # Initialization of HAL modules
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

    keypad.init(key_pressed)
    keypad_thread = Thread(target=keypad.get_key)
    keypad_thread.start()

    lcd = LCD.lcd()
    lcd.lcd_clear()

    lcd.lcd_display_string("Smart Vending", 1)
    lcd.lcd_display_string("System Ready", 2)

    time.sleep(3)

    while True:
        lcd.lcd_clear()
        lcd.lcd_display_string("Enter Item #", 1)

        # Fetch menu from database
        menu = fetch_menu()
        for item in menu:
            print(f"{item[0]}. {item[1]} - ${item[2]:.2f}")

        # Wait for keypad input
        input_buffer = ""
        awaiting_multi_digit_input = True
        while not shared_keypad_queue.qsize():
            lcd.lcd_display_string(f"Input: {input_buffer[:16]}{' ' * (16 - len(input_buffer))}", 2)
            time.sleep(0.1)

        keyvalue = shared_keypad_queue.get()
        awaiting_multi_digit_input = False

        try:
            item_id = int(keyvalue)
            if any(item[0] == item_id for item in menu):
                selected_item = next(item for item in menu if item[0] == item_id)
                initials = get_initials(selected_item[1])
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
                if confirm_key == "1":
                    insert_order(item_id, "local")
                    lcd.lcd_clear()
                    lcd.lcd_display_string("Order Placed", 1)
                    buzzer.beep(0.3, 0.1, 1)
                    time.sleep(2)
                else:
                    lcd.lcd_clear()
                    lcd.lcd_display_string("Cancelled", 1)
                    buzzer.beep(0.2, 0.1, 1)
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

        # Process pending orders
        next_order = fetch_next_order()
        if next_order:
            order_id, item_id = next_order
            selected_item = next(item for item in menu if item[0] == item_id)
            initials = get_initials(selected_item[1])
            lcd.lcd_clear()
            lcd.lcd_display_string("Preparing", 1)
            lcd.lcd_display_string(f"{initials}", 2)
            update_order_status(order_id, "Preparing")
            buzzer.beep(0.2, 0.1, 3)
            time.sleep(5)  # Simulate preparation time
            update_order_status(order_id, "Completed")
            lcd.lcd_clear()
            lcd.lcd_display_string("Completed", 1)
            lcd.lcd_display_string(f"{initials}", 2)
            buzzer.beep(0.3, 0.1, 2)
            time.sleep(2)

if __name__ == "__main__":
    main()
