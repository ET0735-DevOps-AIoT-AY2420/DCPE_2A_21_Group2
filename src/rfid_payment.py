from hal import hal_led as led
from hal import hal_lcd as LCD
from hal import hal_rfid_reader as rfid_reader
import time

# Global variable for simulated RFID payment (if needed)
rfid_balance = 100.00  # starting balance

def simulate_rfid_payment(payment_amount=2.50):
    """
    Waits for an RFID card to be scanned and simulates a payment.
    Returns a tuple: (rfid_card_id, new_balance)
    """
    global rfid_balance
    # Initialize hardware
    lcd = LCD.lcd()
    led.init()
    lcd.backlight(1)
    lcd.lcd_clear()
    lcd.lcd_display_string("Tap RFID card", 1)
    led.set_output(0, 0)
    reader = rfid_reader.init()

    # Wait until a card is detected
    card_id = None
    while card_id is None:
        card_id = reader.read_id_no_block()  # Non-blocking read
        card_id = str(card_id) if card_id is not None else None
        time.sleep(0.1)

    # Display the card ID on the LCD
    lcd.lcd_display_string("ID: " + card_id, 2)
    
    # Process the payment if funds are sufficient
    if rfid_balance >= payment_amount:
        rfid_balance -= payment_amount
        lcd.lcd_display_string("Paid: ${:.2f}".format(payment_amount), 2)
        time.sleep(2)
        lcd.lcd_clear()
        lcd.lcd_display_string("New Balance:", 1)
        lcd.lcd_display_string("${:.2f}".format(rfid_balance), 2)
    else:
        lcd.lcd_display_string("Insufficient funds", 2)
    
    # Return the card id and new balance
    return card_id, rfid_balance
