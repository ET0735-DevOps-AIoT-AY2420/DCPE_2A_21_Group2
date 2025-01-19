import RPi._GPIO as GPIO
from hal import hal_moisture_sensor as moisture
from hal import hal_lcd as lCD
from hal import hal_led as LED
from time import sleep
from telegram import Bot

#initialize Hardware
lcd = lCD.lcd()
lcd.lcd_clear()
moisture.init()
LED.init()

#initialize Telegram Bot
BOT_TOKEN = "7908444221:AAE-oRn61Xp0uOCX_g7vsBgQINPzdhOy6MM"
CHAT_ID = "1947077895"
bot = Bot(token=BOT_TOKEN)

def send_telegram_message(message):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message)
        print(f"Telegram message sent: {message}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

#detect moisture
def moisture_status():
    moisture_status = moisture.read_sensor()

    if moisture_status: # if sensor detects moisture
        lcd.lcd_display_string("Water Level: OK!",1)
        LED.set_output(24, GPIO.LOW)
    else: # if sensor doesn't detect moisture
        lcd.lcd_display_string("Water Level: LOW",1)
        LED.set_output(24, GPIO.HIGH)
        send_telegram_message("The water level is low. Please fill up the water tank.")

#Main function
def main():
    while True:
        moisture_status()
        sleep(10)

#Main entry point
if __name__ == "__main__":
    main()
