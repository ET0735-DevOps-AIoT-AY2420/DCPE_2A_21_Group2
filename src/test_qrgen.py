# test_qr_generator.py
import qrcode
import cv2
import numpy as np
from pyzbar.pyzbar import decode

def generate_qr(data, filename="test_qr.png"):
    """
    Generate a QR code image from the given data and save it to filename.
    Returns the filename.
    """
    # Create QR code image using qrcode library
    qr_img = qrcode.make(data)
    qr_img.save(filename)
    return filename

def decode_qr_from_file(filename):
    """
    Read the saved QR code image and decode it using pyzbar.
    Print the decoded data.
    """
    img = cv2.imread(filename)
    decoded_objects = decode(img)
    if decoded_objects:
        for obj in decoded_objects:
            decoded_text = obj.data.decode("utf-8")
            print("Decoded Data:", decoded_text)
    else:
        print("No QR code detected in the image.")

def display_qr_image(filename):
    """
    Display the saved QR code image using OpenCV.
    Press any key in the display window to close it.
    """
    img = cv2.imread(filename)
    if img is None:
        print("Failed to load image:", filename)
        return
    cv2.imshow("Test QR Code", img)
    print("Press any key in the image window to close it.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # Example test data: "user_id:amount:transaction_id"
    test_data = "1:2.50:TEST123"  # For example, admin user (id 1), $2.50 transaction, test transaction id
    filename = generate_qr(test_data)
    print(f"QR Code generated and saved as '{filename}' with data: {test_data}")

    # Decode the generated QR code to verify its contents.
    decode_qr_from_file(filename)
    
    # Display the generated QR code in a window.
    display_qr_image(filename)