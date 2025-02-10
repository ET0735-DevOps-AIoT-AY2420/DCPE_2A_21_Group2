# pi_scanner.py
from pyzbar.pyzbar import decode
import cv2
import sqlite3
import datetime
import numpy as np

DB_FILE = "vending_machine.db"  # Adjust path if needed

def process_qr_data(qr_data):
    """
    Expected QR data format: "user_id:amount:transaction_id"
    """
    parts = qr_data.split(":")
    if len(parts) != 3:
        print("Invalid QR data format.")
        return

    try:
        user_id = int(parts[0])
        amount = float(parts[1])
        transaction_id = parts[2]
    except ValueError:
        print("QR data contains invalid numbers.")
        return

    # Connect to the database
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Prevent duplicate processing by checking transaction_id.
    cursor.execute("SELECT 1 FROM orders WHERE transaction_id = ?", (transaction_id,))
    if cursor.fetchone():
        print("This transaction has already been processed.")
        conn.close()
        return

    # Check user's credit balance.
    cursor.execute("SELECT credit FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        print("User not found in database.")
        conn.close()
        return

    current_credit = row[0]
    if current_credit < amount:
        print("Insufficient credit for the transaction.")
        conn.close()
        return

    # Deduct the amount from user's credit.
    new_credit = current_credit - amount
    cursor.execute("UPDATE users SET credit = ? WHERE id = ?", (new_credit, user_id))

    # Record the order (source "QR") and mark as Completed.
    current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO orders (user_id, amount, transaction_id, source, status, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, amount, transaction_id, "QR", "Completed", current_timestamp))
    order_id = cursor.lastrowid

    # Record the sale (adjust item_id as needed; here we use 0 as a placeholder).
    cursor.execute("""
        INSERT INTO sales (order_id, item_id, timestamp, price, source)
        VALUES (?, ?, ?, ?, ?)
    """, (order_id, 0, current_timestamp, amount, "QR"))
    conn.commit()
    conn.close()

    print(f"Payment of ${amount:.2f} for user {user_id} processed successfully. New balance: ${new_credit:.2f}")

def main():
    cap = cv2.VideoCapture(0)
    print("Starting QR code scanning. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        qr_codes = decode(frame)
        if qr_codes:
            for qr in qr_codes:
                qr_text = qr.data.decode('utf-8')
                print(f"Detected QR code: {qr_text}")
                process_qr_data(qr_text)
                # Draw a bounding box (optional)
                pts = np.array([point for point in qr.polygon], np.int32)
                cv2.polylines(frame, [pts], True, (255, 0, 0), 2)
                cv2.putText(frame, "Processed", (pts[0][0], pts[0][1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0), 2)
                # Process one QR code per frame.
                break

        cv2.imshow("QR Scanner", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
