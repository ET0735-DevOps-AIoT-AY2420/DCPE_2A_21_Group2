import RPi.GPIO as GPIO
import time
from hal import hal_lcd as LCD
from hal import hal_led as LED
from hal import dht11 as DHT11
from telegram import Bot

DHT_PIN  = 21

# DHT11 Result Class
class DHT11Result:
    
    ERR_NO_ERROR = 0
    ERR_MISSING_DATA = 1
    ERR_CRC = 2

    error_code = ERR_NO_ERROR
    temperature = -1
    humidity = -1

    def __init__(self, error_code, temperature, humidity):
        self.error_code = error_code
        self.temperature = temperature
        self.humidity = humidity

    def is_valid(self):
        return self.error_code == DHT11Result.ERR_NO_ERROR

#initialize Hardware
lcd = LCD.lcd()
lcd.lcd_clear()
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

#initialize temp and humidity sensor
dht11_sensor = DHT11.DHT11(pin=DHT_PIN)

def temp_and_humidity():
    result = dht11_sensor.read()

    if result.is_valid():
        temperature = result.temperature
        humidity = result.humidity

        if 25 <= temperature <= 30:
            LED.set_output(24,GPIO.LOW)
            lcd.lcd_display_string(f"Temp: {temperature}", 1)
            lcd.lcd_display_string(f"Hum: {humidity}%", 2)
            print("Temp is within range")

        elif temperature < 25:
            LED.set_output(24,GPIO.HIGH)
            lcd.lcd_display_string(f"Temp: {temperature}", 1)
            lcd.lcd_display_string(f"Hum: {humidity}%", 2)
            print("Temp is too low")
            send_telegram_message(f"Temp: {temperature}\n " f"Humidity: {humidity}%\n " "The temperature is too low!")

        elif temperature > 30:
            LED.set_output(24,GPIO.HIGH)
            lcd.lcd_display_string(f"Temp: {temperature}", 1)
            lcd.lcd_display_string(f"Hum: {humidity}%", 2)
            print("Temp is too High")
            send_telegram_message(f"Temp: {temperature}\n " f"Humidity: {humidity}%\n " "The temperature is too high!")

        else:
            lcd.lcd_display_string("Error Reading sensor", 1)
            print("Error: Sensor data invalid")

# Main function
def main():
    while True:
        temp_and_humidity()
        time.sleep(10)

# Main entry point
if __name__ == "__main__":
    main() 
