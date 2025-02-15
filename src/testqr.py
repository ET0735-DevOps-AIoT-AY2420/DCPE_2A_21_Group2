import cv2
import os
import time
import sqlite3
import requests
import queue
from picamera2 import Picamera2
from pyzbar.pyzbar import decode
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
import qrcode

shared_keypad_queue = queue.Queue()

# Telegram Bot Details
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"

# Database File
DB_FILE = os.getenv("DB_PATH", "/data/vending_machine.db")

# QR Code Save Path
QR_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qrcodes")
os.makedirs(QR_FOLDER, exist_ok=True)

input_buffer = ""
awaiting_multi_digit_input = False
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


# ✅ Function to Generate and Send QR Code
def generate_and_send_qr(user_id, phone_number, chat_id, order_id):
    """
    Generates a QR code for payment and sends it to the user via Telegram.
    Returns the filename of the QR code.
    """
    qr_data = f"ORDER_{order_id}_{phone_number}"
    qr_filename = os.path.join(QR_FOLDER, f"qr_{order_id}.png")

    qr = qrcode.make(qr_data)
    qr.save(qr_filename)

    # ✅ Send QR Code to Telegram
    files = {"photo": open(qr_filename, "rb")}
    data = {"chat_id": chat_id, "caption": "Scan this QR code to complete payment."}
    response = requests.post(TELEGRAM_API_URL, data=data, files=files)
    
    if response.status_code == 200:
        print("[INFO] QR Code sent to Telegram successfully.")
    else:
        print("[ERROR] Failed to send QR Code to Telegram.")

    return qr_data

# ✅ QR Code Scanning Function
def scan_qr(scan_time=15):
    """
    Opens the camera to scan a QR code for scan_time seconds.
    Returns the scanned QR data or None if scanning fails.
    """
    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(main={"size": (640, 480)})
    picam2.configure(video_config)

    start_time = time.time()
    scanning = True

    picam2.start()
    print("[INFO] QR Scanner started...")

    while scanning:
        frame = picam2.capture_array()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        codes = decode(gray)

        for code in codes:
            qr_data = code.data.decode("utf-8")
            print(f"✅ QR Code Detected: {qr_data}")
            scanning = False
            picam2.stop()
            picam2.close()
            cv2.destroyAllWindows()
            return qr_data

        if time.time() - start_time > scan_time:
            print("[WARNING] QR scanning timed out.")
            scanning = False
            break

    picam2.stop()
    picam2.close()
    cv2.destroyAllWindows()
    return None

# ✅ Integrating QR Payment into Main Program
lcd = LCD.lcd()
shared_keypad_queue = keypad.get_key()

# User selects payment method
lcd.lcd_display_string("1. RFID", 1)
lcd.lcd_display_string("2. QR", 2)
payment_key = shared_keypad_queue.get()

if payment_key == "2":  # ✅ User selects QR Payment
    lcd.lcd_clear()
    lcd.lcd_display_string("Generating QR", 1)
    
    # ✅ Fetch user details from DB
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT phone_number, chat_id FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        lcd.lcd_clear()
        lcd.lcd_display_string("User Not Found", 1)
        time.sleep(2)
        exit()  # Exit QR payment process

    phone_number, chat_id = user

    # ✅ Generate and Send QR
    qr_data = generate_and_send_qr(user_id, phone_number, chat_id, order_id)

    lcd.lcd_clear()
    lcd.lcd_display_string("Scan QR to Pay", 1)
    lcd.lcd_display_string("Opening Camera", 2)
    time.sleep(2)

    # ✅ Open Camera for Scanning
    scanned_qr = scan_qr(15)

    if scanned_qr == qr_data:
        lcd.lcd_clear()
        lcd.lcd_display_string("Payment Success", 1)
        lcd.lcd_display_string("Enjoy Your Drink", 2)
        time.sleep(2)

        # ✅ Mark Order as Paid
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status = 'Paid', payment_source = 'QR' WHERE order_id = ?", (order_id,))
        cursor.execute("""
            INSERT INTO sales (order_id, item_id, timestamp, price, source, payment_source)
            VALUES (?, ?, datetime('now', 'localtime'), ?, 'local', 'QR')
        """, (order_id, item_id, selected_item[2]))
        conn.commit()
        conn.close()

        # ✅ Prepare Drink After Successful Payment
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
        lcd.lcd_clear()
        lcd.lcd_display_string("Payment Failed", 1)
        lcd.lcd_display_string("Try Again", 2)
        time.sleep(2)
