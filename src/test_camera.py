from picamera2 import Picamera2, Preview
from pyzbar.pyzbar import decode
import cv2
import numpy as np
from hal import hal_lcd
import smbus
import time

#initialilsation
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640,480)})
picam2.configure(config)
picam2.start()
lcd = hal_lcd.lcd()

def get_qr_data(input_frame):
    try:
        return decode(input_frame)
    except:
        return[]
    
def draw_polygon(frame_in,qrobj):
    if len(qrobj) == 0:
        return frame_in
    else:
        for obj in qrobj:
            text= obj.data.decode('utf-8')
            pts = obj.polygon
            pts = np.array([pts], np.int32)  # Convert points to NumPy array
            pts = pts.reshape((4, 1, 2))    # Reshape for drawing
            cv2.polylines(frame_in, [pts], True, (255, 55, 5), 2)  # Draw polygon
            cv2.putText(frame_in, text, (50, 50), cv2.FONT_HERSHEY_PLAIN, 1.5, (255, 200, 1), 2)  # Display text

            # Show QR data on LCD
            lcd.lcd_display_string(f"{text[:16]}", 1)
            time.sleep(3)
            lcd.lcd_clear()

            print(text)
        return frame_in

# Main loop
try:
    while True:
        frame = picam2.capture_array()  # Capture a frame as a NumPy array
        qr_obj = get_qr_data(frame)    # Decode QR codes
        frame = draw_polygon(frame, qr_obj)  # Draw polygons around detected QR codes
        
        if len(qr_obj)> 0 :
            frame= draw_polygon(frame,qr_obj)
            time.sleep(3)
            lcd.lcd_clear()
        else:
            # Display the result
            cv2.imshow("QR Code Detection", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):  
            break
finally:
    picam2.stop()
    cv2.destroyAllWindows()
    lcd.lcd_clear()