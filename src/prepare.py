from hal import hal_servo as servo
from hal import hal_buzzer as buzzer
from hal import hal_led as led
from hal import hal_input_switch as switch
from time import sleep

def main():
    # Initialize peripherals
    servo.init()
    buzzer.init()
    led.init()
    switch.init()

    while True:
        # Check the state of the switch
        switch_state = switch.read_slide_switch()
        
        if switch_state:  # Switch is ON
            print("Switch is ON. Preparing drink...")

            # Step 1: Start the drink preparation process
            print("Starting preparation...")
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

            print("Drink preparation completed. Waiting for next order.")

            # Wait until the switch is turned OFF to prevent repeated actions
            while switch.read_slide_switch():
                sleep(0.1)

        else:
            print("Switch is OFF. Waiting for the next order...")
            sleep(0.5)  # Poll the switch state every 0.5 seconds

if __name__ == "__main__":
    main()