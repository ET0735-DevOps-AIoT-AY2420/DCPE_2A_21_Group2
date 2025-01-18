from threading import Thread
from hal import hal_keypad as keypad
from hal import hal_lcd as LCD
from hal import hal_ir_sensor as IR
from hal import hal_led as led_ctrl
from hal import hal_usonic as usonic
from hal import hal_servo as servo
from hal import hal_adc as adc
from picamera2 import Picamera2
import time 
from time import sleep
from telegram import Bot

#door_assigned values
open_door_adc = 255
open_door_angle = 180

closed_door_adc = 0
closed_door_angle = 0

BOT_TOKEN = "7723998968:AAFc4QK-qRaIxCfqeqLYRs1OLuF-2z_OOiM"
CHAT_ID = "5819192033"

# Initialize LCD
lcd = LCD.lcd()
lcd.lcd_clear()

# Initialize Telegram Bot
bot = Bot(token=BOT_TOKEN)

# Admin access variables
ADMIN_PASSCODE = "1234"  # Replace with a secure passcode
admin_logged_in = False  # Flag to track admin access
entered_passcode = ""    # Buffer to store passcode input

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
    if key == "#":
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


def main():

    # Initialize hardware
    lcd.lcd_clear()
    servo.init()
    adc.init()

    # Display initial message
    lcd.lcd_display_string("Admin Login", 1)

    # Initialize keypad
    keypad.init(key_pressed)

    # Start keypad scanning in a new thread
    keypad_thread = Thread(target=keypad.get_key)
    keypad_thread.start()

    while True:
        while True:
            adc_value = adc.get_adc_value(1)
            servo_angle = adc_to_servo_angle(adc_value)
            servo.set_servo_position(servo_angle)  # Set servo position based on angle
            print(f"ADC Value: {adc_value}, Servo Angle: {servo_angle}")
            sleep(0.1)

    # Start door control loop
    #control_door()




# Main entry point
if __name__ == "__main__":
    main()