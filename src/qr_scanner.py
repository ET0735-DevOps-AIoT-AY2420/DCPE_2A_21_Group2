import time
import cv2
from pyzbar.pyzbar import decode
import logging

logger = logging.getLogger(__name__)

def scan_qr_code(camera, timeout=60):
    """
    Uses the provided Picamera2 instance (configured with a 'lores' stream)
    to scan for a QR code within the given timeout.
    
    Args:
      camera: A Picamera2 instance (already configured and started).
      timeout: Maximum seconds to scan.
      
    Returns:
      The decoded QR code string or None if not found.
    """
    start_time = time.time()
    qr_data = None

    while time.time() - start_time < timeout:
        try:
            frame = camera.capture_array("lores")
        except Exception as e:
            logger.error("Error capturing frame: %s", e)
            continue

        if frame is None:
            logger.debug("No frame captured, retrying...")
            continue

        # Assuming the lores stream is YUV420, use its luminance channel (grayscale)
        height, width = frame.shape[:2]
        gray = frame[:height, :width]
        decoded_objects = decode(gray)
        if decoded_objects:
            qr_data = decoded_objects[0].data.decode("utf-8")
            logger.info("QR code detected: %s", qr_data)
            break
        time.sleep(0.1)
    return qr_data

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)
    from picamera2 import Picamera2, Preview
    camera = Picamera2()
    config = camera.create_preview_configuration(
        main={"format": "XRGB8888", "size": (640,480)},
        lores={"format": "YUV420", "size": (320,240)}
    )
    camera.configure(config)
    camera.start_preview(Preview.DRM)
    camera.start()
    logger.info("Scanning for QR code. Please present your QR code to the camera...")
    result = scan_qr_code(camera, timeout=60)
    if result:
        print("QR Code detected:", result)
    else:
        print("No QR code detected within the timeout period.")
    camera.stop_preview()
    camera.stop()
    sys.exit(0)
