import cv2
import os
import time
from datetime import datetime
from threading import Thread
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from pyzbar.pyzbar import decode
import qrcode
import queue
import pytz
import sqlite3
import prepare
import requests
import threading

# Importing hardware abstraction libraries (HALs)
from hal import hal_led as led
from hal import hal_lcd as LCD
from hal import hal_adc as adc
from hal import hal_accelerometer as accel
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
from telegram import Bot

IMAGE_FOLDER = "qrcodes"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

VIDEO_FOLDER = "videos"
os.makedirs(VIDEO_FOLDER, exist_ok=True) 

# Queue for storing keypad inputs
shared_keypad_queue = queue.Queue()

# Database file location
DB_FILE = os.getenv("DB_PATH", "/data/vending_machine.db")

#flag to track security status
intrusion_detected = False

# Define QR Code Save Directory
QR_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qrcodes")
os.makedirs(QR_FOLDER, exist_ok=True)  # Ensure directory exists

# Define Singapore Time Zone
SGT = pytz.timezone('Asia/Singapore')

#encoder for video taken
encoder = H264Encoder(bitrate=10000000)

#setting latest_video_path as none

latest_video_path = None

# Function to Get Current Time in Singapore Time
def get_sg_time():
    return datetime.now(SGT).strftime('%Y-%m-%d %H:%M:%S')

# Correct 4-digit passcode
CORRECT_PASSCODE = "1234"

#for admin
BOT_TOKEN = "7722732406:AAFEAXz_RTJNRAnE9aRnOVtlN18G7V-0wWU"
TELEGRAM_CHAT_ID = 1498916836  

# for user
TELEGRAM_BOT_TOKEN = "7722732406:AAFEAXz_RTJNRAnE9aRnOVtlN18G7V-0wWU"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
bot = Bot(token="7722732406:AAFEAXz_RTJNRAnE9aRnOVtlN18G7V-0wWU")

#for admin
admin_log_in = False

'''def generate_and_send_qr(user_id, phone_number, chat_id, order_id, QR_FOLDER):
    """
    Generates a QR code for payment and sends it to the user via Telegram.
    Returns the filename of the QR code.
    """
    qr_data = f"ORDER_{order_id}_{phone_number}"
    qr_filename = os.path.join(QR_FOLDER, f"qr_{order_id}.png")

    qr = qrcode.make(qr_data)
    qr.save(qr_filename)

    # ✅ Send QR Code to Telegram
    with open(qr_filename, "rb") as qr_file:
        files = {"photo": qr_file}
        data = {"chat_id": chat_id, "caption": "Scan this QR code to complete payment."}
        response = requests.post(TELEGRAM_API_URL, data=data, files=files)

        if response.status_code == 200:
            print("[INFO] QR Code sent to Telegram successfully.")
        else:
            print("[ERROR] Failed to send QR Code to Telegram.")
    return qr_data'''

def is_camera_in_use():
    """Check if another process is using the camera."""
    return "picamera2" in os.popen("ps aux | grep picamera2 | grep -v grep").read()

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


def scan_qr(scan_time=20):
    """Scans a QR code and checks the database."""
    if is_camera_in_use():
        print("Camera is already in use by another process.")
        return False

    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(main={"size": (640, 480)})
    picam2.configure(video_config)

    scanning = True
    qr_detected = False
    start_time = time.time()

    picam2.start()
    print("QR Scanner started...")

    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    while scanning:
        frame = picam2.capture_array()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        codes = decode(gray)

        for code in codes:
            qr_data = code.data.decode("utf-8")
            print(f"QR Code Detected: {qr_data}")

            scanning = False
            picam2.stop()
            picam2.close()
            cv2.destroyAllWindows()
            return qr_data
            
            cursor.execute("SELECT order_id FROM collection_qr_codes WHERE qr_code=? AND status='Pending'", (qr_data,))
            result = cursor.fetchone()            
            '''if result:
                cursor.execute("DELETE FROM TemporaryQR WHERE key_id=?", (qr_data,))
                conn.commit()
                os.remove(f"src/static/qrcodes/{qr_data}.png")
                scanning = False
                qr_detected = True
                break'''
            print(f"✅ QR Code Detected: {qr_data}")

        

        cv2.imshow("QR Code Scanner", frame)

        if time.time() - start_time > scan_time:
            print("Scanning time exceeded.")
            scanning = False

        if cv2.waitKey(1) & 0xFF == ord('q'):
            scanning = False

    picam2.stop()
    picam2.close()
    cv2.destroyAllWindows()

    return None

def send_telegram_video(video_path):
    """Sends the recorded video via Telegram Bot."""
    print(f"Sending video: {video_path}")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    
    with open(video_path, "rb") as video_file:
        response = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID}, files={"video": video_file})
    
    if response.status_code == 200:
        print("Video sent successfully.")
    else:
        print(f"Failed to send video: {response.text}")

def record_and_send_video():
      
    if is_camera_in_use():
        print("Camera is already in use by another process.")
        picam2.close()
        picam2.stop()
        return

    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(main={"size": (640, 480)})
    picam2.configure(video_config)
    encoder = H264Encoder(bitrate=5000000)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    h264_path = os.path.join(VIDEO_FOLDER, f"video_{timestamp}.h264")
    mp4_path = os.path.join(VIDEO_FOLDER, f"video_{timestamp}.mp4")

    try:
        print(f"Recording video: {h264_path}")
        picam2.start_recording(encoder, h264_path)
        time.sleep(10)
        picam2.stop_recording()
        print("Recording complete.")

        print("Converting video to MP4...")
        convert_command = f"ffmpeg -i {h264_path} -c copy {mp4_path} -y"
        result = os.system(convert_command)

        if result == 0 and os.path.exists(mp4_path):
            print("Conversion successful.")
            os.remove(h264_path)  # ✅ Delete the .h264 file after conversion
            send_telegram_video(mp4_path)
        else:
            print("Error: Video conversion failed.")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        picam2.close()
        picam2.stop()

        #if cannot run anymore pls use below function ^,^
'''def record_and_send_video():
    
    if is_camera_in_use():
        print("Camera is already in use by another process.")
        return

    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(main={"size": (640, 480)})
    picam2.configure(video_config)
    encoder = H264Encoder(bitrate=5000000)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output = os.path.join(VIDEO_FOLDER, f"video_{timestamp}.h264")
    mp4_path = output.replace(".h264", ".mp4")

    try:
        print(f"Recording video: {output}")
        picam2.start_recording(encoder, output)
        time.sleep(10)
        picam2.stop_recording()
        print("Recording complete.")

        print("Converting video to MP4...")
        os.system(f"ffmpeg -i {output} -c copy {mp4_path} -y")
        print("Conversion complete.")

        send_telegram_video(mp4_path)

    except Exception as e:
        print(f"Error: {e}")

    finally:
        picam2.close()
        picam2.stop()'''


def send_telegram_photo(image_path, caption):
    """Sends a photo to Telegram."""
    with open(image_path, "rb") as photo:
        response = requests.post(
            TELEGRAM_API_URL,
            data={"chat_id": "5819192033", "caption": caption},
            files={"photo": photo}
        )
    
    if response.status_code == 200:
        print("[INFO] QR Code image sent to Telegram successfully.")
    else:
        print(f"[ERROR] Failed to send image to Telegram: {response.text}")

# Callback function for handling keypress events from the keypad
def key_pressed(key):
    """
    Handles keypress events and manages input buffer for multi-digit inputs.
    """
    global input_buffer, awaiting_multi_digit_input
    print(f"[DEBUG] Key Pressed: {key}")  # ✅ Add debug print

    if awaiting_multi_digit_input and key in range(10):  # If awaiting input, add digits to buffer
        input_buffer += str(key)
        print(f"[DEBUG] Input Buffer: {input_buffer}")  # ✅ Show buffer status

    elif awaiting_multi_digit_input and key == "#":  # Confirm multi-digit input with '#'
        if input_buffer:  # Add to queue only if input exists
            shared_keypad_queue.put(input_buffer)
            print(f"[DEBUG] Sent to Queue: {input_buffer}")  # ✅ Show what's sent to queue
            input_buffer = ""

    elif awaiting_multi_digit_input and key == "*":  # Clear buffer on '*'
        input_buffer = ""
        print("[DEBUG] Buffer Cleared")  # ✅ Debug buffer clear

    elif not awaiting_multi_digit_input and key in range(10):  # Directly handle single-digit inputs
        shared_keypad_queue.put(str(key))
        print(f"[DEBUG] Single Digit Input Sent: {key}")  # ✅ Debug single digit queue


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
def insert_order(item_id, user_id, source, payment_source):
    """
    Inserts a new order into the database with a valid user_id.

    Args:
        item_id (int): ID of the selected menu item.
        user_id (int): ID of the user placing the order.
        source (str): Source of the order (e.g., "local" or "remote").

    Returns:
        int: The order ID of the newly created order.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders (item_id, user_id, source, status, timestamp, payment_source) 
        VALUES (?, ?, ?, 'Pending', ?, ?)
    """, (item_id, user_id, source, get_sg_time(), payment_source))
    
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

def fetch_next_order():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # 🔹 Fetch remote orders from API
        response = requests.get("http://localhost:5000/order")
        if response.status_code == 200:
            remote_orders = response.json()
            for order in remote_orders:
                order_id = order["order_id"]
                item_id = order["item_id"]
                user_id = order.get("user_id", None)  # Ensure `user_id` is stored

                # 🔹 Check if order already exists
                cursor.execute("SELECT order_id FROM orders WHERE order_id = ?", (order_id,))
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO orders (order_id, item_id, user_id, source, status, timestamp)
                        VALUES (?, ?, ?, 'remote', 'Pending', ?)
                    """, (order_id, item_id, user_id, get_sg_time()))
                    conn.commit()
                    print(f"[DEBUG] Inserted Remote Order {order_id}")

        # ✅ Fetch only `Paid` orders that haven't been collected
        cursor.execute("""
            SELECT s.order_id, s.item_id, o.source, o.user_id
            FROM sales s
            JOIN orders o ON s.order_id = o.order_id
            LEFT JOIN collection_qr_codes c ON s.order_id = c.order_id
            WHERE o.status = 'Paid' 
              AND (c.status IS NULL OR c.status != 'Collected')  -- Ignore collected orders
            ORDER BY s.timestamp
            LIMIT 1
        """)

        next_order = cursor.fetchone()
        conn.close()

        return next_order if next_order else None

    except Exception as e:
        print(f"[ERROR] fetch_next_order failed: {e}")
        return None

def send_telegram_message(message):
    try:
        bot.send_message(chat_id=5819192033, text=message)
        print(f"Telegram message sent: {message}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

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

def enter_passcode():
    """Handles passcode input from keypad using shared_keypad_queue and updates LCD dynamically."""
    lcd = LCD.lcd()
    lcd.lcd_clear()
    lcd.lcd_display_string("Enter Passcode:", 1)
    
    input_buffer = ""
    awaiting_multi_digit_input = True

    while not shared_keypad_queue.qsize():
        lcd.lcd_display_string(f"{input_buffer[:16]}{' ' * (16 - len(input_buffer))}", 2)
        time.sleep(0.1)
                
    passcode = shared_keypad_queue.get()
    return passcode  # Return entered passcode

def get_user_id(phone_number):
    """
    Retrieves the user_id from the database based on the provided phone number.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE phone_number = ?", (phone_number,))
    user = cursor.fetchone()
    conn.close()
    return user[0] if user else None  # Return user_id if found, else None

def monitor_security():
    """
    Background thread to monitor ultrasonic sensor.
    Sends an alert immediately if the distance is less than 5 cm.
    """
    global intrusion_detected
    
    usonic.init()
    ir_sensor.init()
    acc = accel.init()  # Initialize accelerometer
    buzzer.init()

    intrusion_start_time = None

    last_x, last_y, last_z = acc.get_3_axis()  # Get initial accelerometer readings

    while True:
        distance = usonic.get_distance()
        current_x, current_y, current_z = acc.get_3_axis()
        if distance < 5 and ir_sensor.get_ir_sensor_state(): 
            if not admin_log_in: # Object too close + IR triggered
                if not intrusion_detected:  # Prevent multiple alerts
                    print("[SECURITY] Intrusion detected! Sending alert...")
                    send_telegram_message(" Alert: Someone is holding the door!")
                    buzzer.beep(0.2, 0.3, 5)
                    intrusion_detected = True  
            else: 
                    intrusion_detected = False
        elif abs(current_x - last_x) > 0.07 or abs(current_y - last_y) > 0.07 or abs(current_z - last_z) > 0.07:
            if not admin_log_in:  # Prevent multiple alerts
                if not intrusion_detected:
                    print("[SECURITY] Machine movement detected! Possible tampering!")
                    send_telegram_message(" Alert: Machine movement detected! Possible tampering!")
                    buzzer.beep(0.3, 0.2, 2)
                    intrusion_detected = True
            else:
                    intrusion_detected = False
        else:
            intrusion_detected = False  # Reset if object moves away

        last_x, last_y, last_z = current_x, current_y, current_z

        time.sleep(0.5)  # Small delay to optimize CPU usage


def main():
    """
    Main function to handle the vending machine's operations.
    """
    global input_buffer, awaiting_multi_digit_input
    global failed_attempt, rfid_pay, qr_pay
    global admin_log_in

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
    failed_attempt = 0
    admin_log_in=False

    security_thread = threading.Thread(target=monitor_security)
    security_thread.daemon = True
    security_thread.start()

    # Initialize LCD display
    lcd = LCD.lcd()
    lcd.lcd_clear()

    lcd.lcd_display_string("Smart Vending", 1)
    lcd.lcd_display_string("System Ready", 2)
    time.sleep(3)

    while True:
        if intrusion_detected:
            time.sleep(5)  # Allow time before retrying
            continue
        # Continuously check and process any pending orders first (Remote or Local)
        while True:
            next_order = fetch_next_order()
            if next_order:
                order_id, item_id, source, user_id = next_order  # Include user_id

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
        
        lcd.lcd_clear()
        lcd.lcd_display_string("1. Admin", 1)
        lcd.lcd_display_string("2. Customer", 2)
        
        input_buffer = ""
        awaiting_multi_digit_input = False
        key = shared_keypad_queue.get()

        if key == "1":    
            lcd.lcd_clear()
            lcd.lcd_display_string("Enter Passcode :", 1)
            time.sleep(2)

            input_buffer = ""
            awaiting_multi_digit_input = True
            while not shared_keypad_queue.qsize():
                lcd.lcd_display_string(f"{'*' * len(input_buffer):16}", 2)
                time.sleep(0.1)
                
            passcode = shared_keypad_queue.get()            
            if passcode == CORRECT_PASSCODE:
                failed_attempt = 0  #Reset failed attempts on success
                lcd.lcd_clear() 
                lcd.lcd_display_string("Access Granted", 1)
                send_telegram_message("Admin has logged in")
                admin_log_in = True
                servo.set_servo_position(0)
                time.sleep(2)
                servo.set_servo_position(180)
                time.sleep(2)
                lcd.lcd_clear()
                lcd.lcd_display_string("Enter Passcode", 1)
                while not shared_keypad_queue.qsize():
                    lcd.lcd_display_string(f"{'*' * len(input_buffer):16}", 2)
                    time.sleep(0.1)
                    
                passcode = shared_keypad_queue.get()            
                if passcode == CORRECT_PASSCODE:
                    lcd.lcd_clear()
                    lcd.lcd_display_string("successfully log out", 1)
                    send_telegram_message("Admin has logged out")
                    time.sleep(2)
                    servo.set_servo_position(0)
                    time.sleep(2)
                    servo.set_servo_position(180)
                    time.sleep(2)
                    servo.set_servo_position(0)
                    time.sleep(0)
                    admin_log_in=False
            else:
                failed_attempt += 1  #Increment failed attempts
                lcd.lcd_clear()
                lcd.lcd_display_string("Access Denied", 1)
                buzzer.beep(0.5, 0.5, 2)
                time.sleep(2)
                # ✅ If failed attempts reach 3, send alert and reset counter
                if failed_attempt >= 2:
                    lcd.lcd_clear()
                    lcd.lcd_display_string("Too Many Attempts!", 1)
                    time.sleep(3)
                    record_and_send_video()
                    time.sleep(1)
                    failed_attempt = 0
           
        #Customer            
        elif key == "2":
            lcd.lcd_clear()
            lcd.lcd_display_string("Enter Phone No:", 1)
            
            input_buffer = ""
            awaiting_multi_digit_input = True
            while not shared_keypad_queue.qsize():
                lcd.lcd_display_string(f"{input_buffer[:16]}{' ' * (16 - len(input_buffer))}", 2)
                time.sleep(0.1)
                
            phone_number = shared_keypad_queue.get()
            awaiting_multi_digit_input = False

            user_id = get_user_id(phone_number)

            if not user_id:
                print("[ERROR] Invalid phone number. User not found.")
                lcd.lcd_clear()
                lcd.lcd_display_string("Invalid Number", 1)
                time.sleep(2)
                continue  # Retry phone number entry

            lcd.lcd_clear()
            lcd.lcd_display_string("Welcome!", 1)
            time.sleep(2)

            #Collect Drink or Order
            lcd.lcd_clear()
            lcd.lcd_display_string("1. Collect", 1)
            lcd.lcd_display_string("2. Order", 2)

            input_buffer = ""
            select_mode_key = shared_keypad_queue.get()

            if select_mode_key == "1":
                lcd.lcd_clear()
                lcd.lcd_display_string("Scan your", 1)
                lcd.lcd_display_string("QR code", 2)
                time.sleep(2)

                # ✅ Fetch user details from DB
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("SELECT phone_number, chat_id, credit FROM users WHERE user_id = ?", (user_id,))
                qr_data = cursor.fetchone()
                conn.close()
                
                # ✅ Open Camera for Scanning
                scanned_qr = scan_qr(30)
                print(f"[DEBUG] Im inside main Scanned QR Output: {scanned_qr}")

                # ✅ Validate scanned QR
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("SELECT order_id FROM collection_qr_codes WHERE qr_code=? AND status='Pending'", (scanned_qr,))
                cursor.execute("SELECT rfid_card_id, credit FROM users WHERE user_id = ?", (user_id,))
                result = cursor.fetchone()
                conn.commit()
                conn.close()
                
                if result:
                    servo.set_servo_position(90)
                    time.sleep(2)
                    servo.set_servo_position(0)                 
                else:
                    break    
                                                
            elif select_mode_key == "2":
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
                            order_id = insert_order(item_id, user_id, "local", "RFID")
                            
                            lcd.lcd_clear()
                            lcd.lcd_display_string("Procceding to",1)
                            lcd.lcd_display_string("Payment",2)
                            time.sleep(1)
                            lcd.lcd_clear()
                            lcd.lcd_display_string("1. RFID", 1)
                            lcd.lcd_display_string("2. QR", 2)
                            payment_key = shared_keypad_queue.get()
                            
                            if payment_key == "1":  # ✅ User selects RFID payment
                                rfid_pay = True
                                qr_pay = False
                                lcd.lcd_clear()
                                lcd.lcd_display_string("Scan RFID Card", 1)
                        
                                # ✅ Fetch user's RFID card ID from database
                                conn = sqlite3.connect(DB_FILE)
                                cursor = conn.cursor()
                                cursor.execute("SELECT rfid_card_id, credit FROM users WHERE user_id = ?", (user_id,))
                                #user = cursor.fetchone()
                                rfid_data  = cursor.fetchone()
                                conn.close()

                                if not rfid_data or not rfid_data[0] :
                                    lcd.lcd_clear()
                                    lcd.lcd_display_string("No RFID Linked", 1)
                                    lcd.lcd_display_string("Use QR Instead", 2)
                                    time.sleep(2)
                                    continue  # Go back to payment selection

                                user_rfid, user_credit = rfid_data  # ✅ Safe unpacking
                                
                              

                                paid = False
                                start_time = time.time()  # Get the start time
                                while time.time() - start_time < 10:  # Run for 10 seconds
                                    user_rfid, user_credit = rfid_data
                                    # ✅ Wait for user to scan their RFID card
                                    scanned_rfid = reader.read_id_no_block()
                                    scanned_rfid = str(scanned_rfid)                                                   
                                    if scanned_rfid is None or scanned_rfid == "" or str(scanned_rfid).strip().lower() == "none":
                                        continue
                                        paid = False
                                    elif scanned_rfid != user_rfid:
                                        lcd.lcd_clear()
                                        lcd.lcd_display_string("Invalid Card!", 1)
                                        lcd.lcd_display_string("Try Again", 2)
                                        buzzer.beep(0.5, 0.1, 2)
                                        time.sleep(2)
                                        paid = False
                                    else:                                        
                                        paid = True
                                        break

                            #QR payment             
                            elif payment_key == "2":
                                rfid_pay = False
                                qr_pay = True
                                lcd.lcd_clear()
                                lcd.lcd_display_string("Generating QR", 1)
                                time.sleep(2)

                                # ✅ Fetch user details from DB
                                conn = sqlite3.connect(DB_FILE)
                                cursor = conn.cursor()
                                cursor.execute("SELECT phone_number, chat_id, credit FROM users WHERE user_id = ?", (user_id,))
                                qr_data = cursor.fetchone()
                                conn.close()

                                if not qr_data or not qr_data[0]:
                                    lcd.lcd_clear() 
                                    lcd.lcd_display_string("User Not Found", 1)
                                    time.sleep(2)
                                    continue  # Go back to payment selection                                
                                                                
                                phone_number, chat_id, user_credit = qr_data

                                # ✅ Generate QR Code for this transaction
                                qr_data = f"ORDER_{order_id}_{phone_number}"
                                qr_filename = os.path.join(QR_FOLDER, f"qr_{order_id}.png")

                                qr = qrcode.make(qr_data)
                                qr.save(qr_filename)

                                # ✅ Insert QR Code into TemporaryQR table
                                conn = sqlite3.connect(DB_FILE)
                                cursor = conn.cursor()
                                cursor.execute("""
                                    INSERT INTO collection_qr_codes (order_id, phone_number, chat_id, qr_code, status, timestamp)
                                    VALUES (?, ?, ?, ?, 'Pending', ?)
                                """, (order_id, phone_number, chat_id, qr_data, get_sg_time()))
                                conn.commit()
                                conn.close()

                                # ✅ Send QR image to Telegram
                                with open(qr_filename, "rb") as qr_file:
                                    files = {"photo": qr_file}
                                    data = {"chat_id": chat_id, "caption": "Scan this QR code to complete payment."}
                                    response = requests.post(TELEGRAM_API_URL, data=data, files=files)

                                lcd.lcd_clear()
                                lcd.lcd_display_string("Scan QR to Pay", 1)
                                lcd.lcd_display_string("Opening Camera", 2)
                                time.sleep(2)

                                # ✅ Open Camera for Scanning
                                scanned_qr = scan_qr(30)
                                print(f"[DEBUG] Scanned QR Output: {scanned_qr}")

                                # ✅ Validate scanned QR
                                conn = sqlite3.connect(DB_FILE)
                                cursor = conn.cursor()
                                cursor.execute("SELECT order_id FROM collection_qr_codes WHERE qr_code=? AND status='Pending'", (scanned_qr,))
                                cursor.execute("SELECT rfid_card_id, credit FROM users WHERE user_id = ?", (user_id,))
                                result = cursor.fetchone()
                                conn.commit()
                                conn.close()
                                paid = False

                                if result:
                                    paid = True
                                  
                                else:                                    
                                    paid = False

                            conn = sqlite3.connect(DB_FILE)
                            cursor = conn.cursor()
                            # ✅ Check if the user has enough balance
                            cursor.execute("SELECT price FROM menu WHERE id = ?", (item_id,))
                            item_price = cursor.fetchone()
                            
                            if item_price is None or user_credit < item_price[0]:  # ✅ Use index instead of dictionary access
                                lcd.lcd_clear()
                                lcd.lcd_display_string("Insufficient", 1)
                                lcd.lcd_display_string("Balance!", 2)
                                buzzer.beep(0.5, 0.1, 3)
                                time.sleep(2)
                                conn.close()  # ✅ Close connection before exiting
                                paid = False
                                continue  # Restart payment process
                            conn.commit()
                            conn.close()
                                               
                            if (paid):
                                conn = sqlite3.connect(DB_FILE)
                                cursor = conn.cursor()    
                                # ✅ Deduct amount and update balance
                                new_credit = user_credit - item_price[0]  # ✅ Use index instead of `item_price["price"]`
                                cursor.execute("UPDATE users SET credit = ? WHERE user_id = ?", (new_credit, user_id))
                                if(rfid_pay):
                                    # ✅ Mark order as paid
                                    cursor.execute("UPDATE orders SET status = 'Paid', payment_source = 'RFID' WHERE order_id = ?", (order_id,))
                                    # ✅ Log payment in sales table
                                    cursor.execute("""
                                    INSERT INTO sales (order_id, item_id, timestamp, price, source, payment_source)
                                    VALUES (?, ?, ?, ?, 'local', 'RFID')
                                    """, (order_id, item_id, get_sg_time(), item_price[0]))
                                else :
                                    cursor.execute("UPDATE orders SET status = 'Paid', payment_source = 'QR' WHERE order_id = ?", (order_id,))
                                    cursor.execute("""
                                    INSERT INTO sales (order_id, item_id, timestamp, price, source, payment_source)
                                    VALUES (?, ?, ?, ?, 'local', 'QR')
                                    """, (order_id, item_id, get_sg_time(), item_price[0]))
                                
                                rfid_pay = False
                                qr_pay = False
                                conn.commit()
                                conn.close()  # ✅ Ensure connection is only closed at the end
                                lcd.lcd_clear()
                                lcd.lcd_display_string("Payment Success", 1)
                                lcd.lcd_display_string("Enjoy Your Drink!", 2)
                                time.sleep(2)
                                lcd.lcd_clear()
                                lcd.lcd_display_string(f"Preparing #{item_id}", 1)

                                # ✅ Check if the order status is 'Paid' before preparing the drink
                                conn = sqlite3.connect(DB_FILE)
                                cursor = conn.cursor()
                                cursor.execute("SELECT status FROM orders WHERE order_id = ?", (order_id,))
                                order_status = cursor.fetchone()
                                conn.close()

                                if order_status and order_status[0] == "Paid":
                                    if prepare.prepare_drink(item_id):
                                        update_order_status(order_id, "Completed")
                                        lcd.lcd_clear()
                                        lcd.lcd_display_string("Drink Ready!", 1)
                                    else:
                                        update_order_status(order_id, "Failed")
                                        lcd.lcd_clear()
                                        lcd.lcd_display_string("Prep Failed", 1)
                                    time.sleep(2)
                                else:
                                    print(f"[ERROR] Order {order_id} is not paid. Skipping preparation.")
                                    lcd.lcd_clear()
                                    lcd.lcd_display_string("Payment Required", 1)
                                    time.sleep(2)
                            else:
                                    print(f"[ERROR] Order {order_id} is not paid. Skipping preparation.")
                                    lcd.lcd_clear()
                                    lcd.lcd_display_string("Payment Required", 1)
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
            else:
                continue
        else:
            continue


if __name__ == "__main__":
    main()
