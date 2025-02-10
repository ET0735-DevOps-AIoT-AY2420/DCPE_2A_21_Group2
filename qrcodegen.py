import qrcode, uuid

# Assume we obtained user_id and amount from session/form
user_id = session.get('user_id')
amount = float(request.form['amount'])
transaction_id = uuid.uuid4().hex  # generate a unique transaction ID

# Create QR data string (e.g., "user:amount:transaction")
qr_data = f"{user_id}:{amount}:{transaction_id}"
img = qrcode.make(qr_data)              # Generate QR code image&#8203;:contentReference[oaicite:0]{index=0}
img.save("transaction_qr.png")          # Save to a file
