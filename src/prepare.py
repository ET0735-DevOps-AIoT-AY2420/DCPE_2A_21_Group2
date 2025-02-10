import time
import sqlite3
from hal import hal_servo as servo
from hal import hal_buzzer as buzzer
from hal import hal_led as led
from time import sleep

# Initialize hardware components
servo.init()
buzzer.init()
led.init()

# Database File Location
DB_FILE = "vending_machine.db"

def update_inventory(drink_id):
    """
    Deducts 2 units from the respective inventories for the selected drink.

    Args: 
        drink_id(int)

    Returns:
        bool: True if inventory updated successfully, False otherwise.

    """

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Get the inventory items associated with the drink
        cursor.execute("SELECT inventory_id FROM menu_inventory WHERE id = ?", (drink_id,))
        inventory_ids = cursor.fetchall()

        # No inventory linked to the drink
        if not inventory_ids:
            print(f" [ERROR] No inventory found for Drink ID {drink_id}.")
            conn.close()
            return False
        
        #Deduch 2 units from respective inventories
        for inventory_id in inventory_ids:
            cursor.execute("UPDATE inventory_list SET amount = amount - 2 WHERE inventory_id = ?", (inventory_id[0],))

        conn.commit()
        conn.close()
            
        print(" [DEBUG] Inventory updated successfully after preparation.")
        return True
    except Exception as e:
        print(f" [ERROR] Database error while updating inventory: {e}")
        return False
    
def prepare_drink(drink_id):
    """
    Prepares a drink using the servo motor, buzzer, and LED.
    
    Args:
        drink_id (int): The ID of the drink to prepare.
    
    Returns:
        bool: True if preparation is successful, False otherwise.
    """
    try:
        # Step 1: Start the drink preparation process
        print(f"Starting preparation for Drink #{drink_id}")
        buzzer.beep(0.2, 0.2, 1)  # Short beep to indicate start
        sleep(1)
        # Step 2: Servo simulates pouring the drink
        print("Pouring drink...")
        servo.set_servo_position(90)  # Move servo to simulate pouring
        sleep(2)  # Simulate pouring time
        servo.set_servo_position(180)  # Return servo to resting position
        sleep(1)

        # Step 3: Buzzer indicates completion of pouring
        print("Pouring completed.")
        buzzer.beep(0.1, 0.1, 3)  # 3 short beeps for completion

        # Step 4: LED lights up to indicate drink is ready
        print("Drink is ready!")
        led.set_output(1, 1)  # Turn on LED to indicate readiness
        led.set_output(1, 0)  # Turn off LED

        # Step 5: Cup collecting mechanism
        servo.set_servo_position(90)  # Move servo to simulate cup dropping
        sleep(2)  # Simulate pouring time
        servo.set_servo_position(180)  # Return servo to resting position
        sleep(1)
        print("ready to collect")

        # Step 6: Reset the servo motor
        print("Resetting system...")
        servo.set_servo_position(0)
        sleep(1)
    
        print(f"Drink #{drink_id} is ready!")

        if update_inventory(drink_id):
            print(f" [DEBUG] Inventory updated.")
        else:
            print(f" [ERROR] Failed to update inventory.")
        return True
    
    except Exception as e:
        print(f"Error during preparation: {e}")
        return False