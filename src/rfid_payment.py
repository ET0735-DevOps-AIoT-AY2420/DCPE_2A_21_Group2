from hal import hal_led as led
from hal import hal_lcd as LCD
from hal import hal_rfid_reader as rfid_reader
import time

# Global variables for simulated RFID payment
rfid_balance = 100.00  # Starting balance in dollars
payment_amount = 2.50  # Fixed payment amount per RFID scan

def main():
    global rfid_balance
    # Initialize LCD and LED
    lcd = LCD.lcd()
    led.init()
    
    # Turn on backlight and clear the display
    lcd.backlight(1)
    lcd.lcd_clear()

    # Display a welcome message on LCD line 1
    lcd.lcd_display_string("Tap RFID card", 1) 

    # Turn off LED (or set to a default state)
    led.set_output(0, 0)

    # Initialize the RFID card reader
    reader = rfid_reader.init()

    # Infinite loop to scan for RFID cards and process payment
    while True:
        card_id = reader.read_id_no_block()
        card_id = str(card_id)
        
        if card_id != "None":
            print("RFID card ID = " + card_id)
            # Display the RFID card ID on LCD line 2
            lcd.lcd_display_string("ID: " + card_id, 2)
            
            # Simulate a payment using RFID:
            if rfid_balance >= payment_amount:
                rfid_balance -= payment_amount
                print("Payment of ${:.2f} processed successfully.".format(payment_amount))
                print("New balance: ${:.2f}".format(rfid_balance))
                # Display payment confirmation and new balance on LCD
                lcd.lcd_display_string("Paid: ${:.2f}".format(payment_amount), 2)
                time.sleep(2)  # Pause to show the payment confirmation
                lcd.lcd_clear()
                lcd.lcd_display_string("New Balance:", 1)
                lcd.lcd_display_string("${:.2f}".format(rfid_balance), 2)
            else:
                print("Insufficient funds for payment!")
                lcd.lcd_display_string("Insufficient funds", 2)
            
            # Wait before the next reading to avoid multiple deductions on a single scan
            time.sleep(3)
            lcd.lcd_clear()
            lcd.lcd_display_string("Tap RFID card", 1)
        # Add a short sleep to reduce CPU usage
        time.sleep(0.1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("RFID payment simulation terminated.")
