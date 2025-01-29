from threading import Thread
from hal import hal_keypad as keypad
from hal import hal_lcd as LCD
from hal import hal_ir_sensor as IR
from hal import hal_led as led_ctrl
from hal import hal_usonic as usonic
from hal import hal_servo as servo
from hal import hal_adc as adc
import time
from time import sleep
from telegram import Bot
from picamera2 import Picamera2
import os
from datetime import datetime
import camera as camera


BOT_TOKEN = "7723998968:AAFc4QK-qRaIxCfqeqLYRs1OLuF-2z_OOiM"
CHAT_ID = "5819192033"

# Initialize LCD
lcd = LCD.lcd()
lcd.lcd_clear()

# Initialize Telegram Bot
bot = Bot(token=BOT_TOKEN)

# Admin access variables
ADMIN_PASSCODE = "1244"  # Replace with a secure passcode
admin_logged_in = False  # Flag to track admin access
entered_passcode = ""    # Buffer to store passcode input

message_sent = False

# Video file path
VIDEO_DIR = "videos"

def admin_lcd_output():
    lcd.lcd_display_string("Enter Admin Code:", 1)
    lcd.lcd_display_string("*" * len(entered_passcode), 2)  # Mask input with asterisks

# Function to handle admin login
def handle_admin_login(key):
    global entered_passcode, admin_logged_in

    # Add the key to the entered passcode
    entered_passcode += str(key)
    lcd.lcd_clear()
    admin_lcd_output()

    # Check if the passcode is complete
    if len(entered_passcode) == len(ADMIN_PASSCODE):
        if entered_passcode == ADMIN_PASSCODE:
            admin_logged_in = True
            lcd.lcd_clear()
            lcd.lcd_display_string("Access Granted", 1)
            lcd.lcd_display_string("Press # to log out", 2)
            print("Admin access granted.")
            send_telegram_message("Admin logged in successfully.")
            if key_pressed=='#':
                admin_logged_in = False
                lcd.lcd_clear()
                admin_lcd_output()
                send_telegram_message("Admin logged out successfully.")
        else:
            lcd.lcd_clear()
            lcd.lcd_display_string("Access Denied", 1)
            print("Admin access denied.")
            send_telegram_message("Failed admin login attempt.")
        entered_passcode = ""  # Reset passcode buffer

# Modify the key_pressed function to loop back to admin login on logout
def key_pressed(key):
    global admin_logged_in

    if not admin_logged_in:
        # If admin is not logged in, check for admin login
        handle_admin_login(key)
        return

    # Admin functionalities start here
    if key == "4":
        # Log out the admin
        admin_logged_in = False
        lcd.lcd_clear()
        lcd.lcd_display_string("Logged Out", 1)
        time.sleep(2)
        admin_lcd_output()  # Redirect to admin login
        return

    # Admin-specific functionality can be added here
    lcd.lcd_clear()
    lcd.lcd_display_string("Admin Logged In", 1)
    lcd.lcd_display_string("Press # to log out", 2)

# Function to send Telegram message
def send_telegram_message(message):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message)
        print(f"Telegram message sent: {message}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")


def adc_to_servo_angle(adc_value):
    # Assuming adc_value ranges from 0 to 1023
    angle = (adc_value * 180) / 1023
    return angle

def handle_sensors():
    """Monitor sensors and trigger alerts if necessary."""
    global message_sent

    IR.init()
    usonic.init()
    distance = usonic.get_distance()

    if distance < 15 and IR.get_ir_sensor_state():
        print("Intrusion detected!")
        if not message_sent:
            if not admin_logged_in:
                send_telegram_message("Alert: Someone is holding the door!")
                camera.take_videos()
                camera.send_latest_video()
                message_sent = True
    else:
        message_sent = False

def operate_servo():
    """Control servo motor based on ADC input."""
    adc_value = adc.get_adc_value(1)
    angle = adc_to_servo_angle(adc_value)
    servo.set_servo_position(angle)

def main():

    """Main program entry point."""
    global admin_logged_in

    lcd.lcd_clear()
    lcd.lcd_display_string("Admin Login", 1)

    # Initialize hardware components
    keypad.init(key_pressed)
    servo.init()
    adc.init()

    # Start keypad listener in a separate thread
    keypad_thread = Thread(target=keypad.get_key)
    keypad_thread.start()

    while True:
        handle_sensors()
        if admin_logged_in:
            operate_servo()
        else:
            # Check ADC value to determine if the door is unlocked
            adc_value = adc.get_adc_value(1)
            if adc_value < 1000:  # If the angle is below 10 degrees
                send_telegram_message("Warning: Admin forgot to lock the door!")
        
        sleep(1)



# Main entry point
if __name__ == "__main__":
    main()
