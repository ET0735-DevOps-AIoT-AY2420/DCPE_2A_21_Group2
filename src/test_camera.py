import os
import time
import cv2
import sys
from picamera2 import Picamera2
from pyzbar.pyzbar import decode

# Ensure UTF-8 for proper logging (optional)
sys.stdout.reconfigure(encoding='utf-8')

def is_camera_in_use():
    """Check if another process is using the camera."""
    return "picamera2" in os.popen("ps aux | grep picamera2 | grep -v grep").read()

def scan_qr(scan_time=30):
    """
    Scan QR code using Raspberry Pi camera.
    Stops when a QR code is detected or after scan_time seconds.
    """
    if is_camera_in_use():
        print("[ERROR] Camera is already in use by another process.")
        return None

    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(main={"size": (640, 480)})
    picam2.configure(video_config)

    scanning = True
    start_time = time.time()

    picam2.start()
    print("[INFO] QR Scanner started...")

    while scanning:
        frame = picam2.capture_array()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        codes = decode(gray)

        for code in codes:
            qr_data = code.data.decode("utf-8")
            print(f"✅ QR Code Detected: {qr_data}")

            # Stop scanning after detecting a QR code
            scanning = False
            picam2.stop()
            picam2.close()
            cv2.destroyAllWindows()
            return qr_data

        # Show the camera feed
        cv2.imshow("QR Code Scanner", frame)

        # Stop scanning if time limit is exceeded
        if time.time() - start_time > scan_time:
            print("[WARNING] Scanning timed out.")
            scanning = False
            break

        if cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to manually stop
            print("[INFO] Scan manually stopped.")
            scanning = False
            break

    picam2.stop()
    picam2.close()
    cv2.destroyAllWindows()
    return None

if __name__ == "__main__":
    qr_data = scan_qr()
    if qr_data:
        print(f"✅ Scanned QR Code: {qr_data}")
    else:
        print("❌ No QR code detected.")
