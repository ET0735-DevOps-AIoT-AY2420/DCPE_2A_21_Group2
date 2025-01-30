from hal import hal_led as led
from hal import hal_lcd as LCD
from hal import hal_rfid_reader as rfid_reader

def main():

    # Get lcd instance
    lcd = LCD.lcd()

    # initialize LED HAL driver
    led.init()

    lcd.backlight(1)
    lcd.lcd_clear()

    # Display message on LCD
    lcd.lcd_display_string("Tap RFIF cards", 1) 

    # Turn off LED
    led.set_output(0, 0);

    # Initialize RFID card reader
    reader = rfid_reader.init()

    # Infinite loop to scan for RFID cards
    while True:
        id = reader.read_id_no_block()
        id = str(id)
        
        if id != "None":
            print("RFID card ID = " + id)
            
            # Display RFID card ID on LCD line 2
            lcd.lcd_display_string(id, 2) 


#Main entry point
if __name__ == "__main__":
    main()



