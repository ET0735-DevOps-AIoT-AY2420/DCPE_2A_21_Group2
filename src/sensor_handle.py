import RPi.GPIO as GPIO  # Correct import
from hal import hal_moisture_sensor as moisture
from hal import hal_led as LED
from hal import dht11 as DHT11
from time import sleep
from telegram import Bot

DHT_PIN = 21

#DHT11 Result Class
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
    
    def is_Valid(self):
        return self.error_code == DHT11Result.ERR_NO_ERROR

# Initialize Hardware
moisture.init()
LED.init()

# Initialize temp and humidity sensor
dht11_sensor = DHT11.DHT11(pin=DHT_PIN)

# Initialize Telegram Bot
BOT_TOKEN = "7908444221:AAE-oRn61Xp0uOCX_g7vsBgQINPzdhOy6MM"
CHAT_ID = "1947077895"
bot = Bot(token=BOT_TOKEN)

def send_telegram_message(message):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message)
        print(f"Telegram message sent: {message}")  # Ensuring there is an indented block inside the function
    except Exception as e:
        print(f"Error sending Telegram message: {e}")  # Fixed missing print statement

# Detect moisture
def moisture_status():
    moisture_level = moisture.read_sensor()  # Renamed for clarity

    if moisture_level:  # If sensor detects moisture
        LED.set_output(24, GPIO.HIGH)
        send_telegram_message("Water Leakage detected. Technician access needed!")
    else:  # If sensor doesn't detect moisture
        LED.set_output(24, GPIO.LOW)

# Detect temperature and humidity
def temp_and_humidity():
    result = dht11_sensor.read()

    if result.is_valid():
        temperature = result.temperature
        humidity= result.humidity

    if 25 <= temperature <= 30:
        LED.set_output(24,GPIO.LOW)
        
    elif temperature < 25:
        LED.set_output(24,GPIO.HIGH)
        send_telegram_message(f"Temp: {temperature}\n" f"Humidity: {humidity}%\n" "The temperature is too Low!." "Technician access needed")

    elif temperature > 30:
        LED.set_output(24,GPIO.HIGH)
        send_telegram_message(f"Temp: {temperature}\n" f"Humidity: {humidity}%\n" "The temperature is too High!." "Technician access needed")


# Main function
def main():
    while True:
        moisture_status()
        temp_and_humidity()
        sleep(10)

# Main entry point
if __name__ == "__main__":
    main()