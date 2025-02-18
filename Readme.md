;# Smart Drink Vending Machine

## 📌 Project Overview
The **Smart Drink Vending Machine** is an innovative vending system designed to allow customers to purchase drinks both **physically at the vending machine** and **remotely via their smartphones or an external website**. The system integrates multiple payment methods, security features, and environmental monitoring to ensure optimal operation.

---

## 🎯 Customer Requirements
### ✅ Ordering & Payment
- Customers can purchase drinks **physically** using a **numeric keypad and LCD screen**.
- Remote orders can be placed via **a smartphone or website**.
- Payment options:
  - **RFID card reader**
  - **QR code or Barcode scanning** via a camera connected to the vending machine
  - **Other electronic payment methods** (future enhancements)

### ✅ Collection System
- Drinks ordered remotely can be collected using a **QR code or Barcode**.
- The generated code is scanned by a **camera connected to the vending machine**.

### ✅ Security & Anti-Theft Features
- **Burglar detection system** to detect if the vending machine door has been pried open.
- If unauthorized access is detected:
  - **Buzzer alarm** is triggered.
  - **Image is captured** and sent to the service team.

### ✅ Environmental Monitoring
- The vending machine maintains **optimal conditions for drink storage**.
- Alerts are sent to technicians if **environmental controls fail**.

### ✅ Technician & Supplier Access
- Service technicians and drinks suppliers must enter a **valid user code** on the **keypad** to open the vending machine without triggering the **buzzer alarm**.

---

## 🏗️ System Architecture

The system is built using:
- **Hardware Components**:
  - Raspberry Pi (Main controller)
  - Keypad for drink selection
  - LCD display for interaction
  - RFID card reader
  - Camera for QR/Barcode scanning
  - Buzzer for security alert
- **Software Stack**:
  - Python (Flask for the web application)
  - SQLite for data storage
  - HTML, CSS, JavaScript for the front-end UI
  - Flask-SQLAlchemy for database interactions
  - Flask-CORS for handling cross-origin requests

---

## 📌 Features
### 🎯 **Remote & Physical Ordering**
Customers can order drinks either at the vending machine or remotely through a smartphone/web interface.

### 🔒 **Security & Anti-Theft Measures**
If unauthorized access is detected, the system captures an image and notifies the service team.

### 🌡 **Environmental Monitoring**
Alerts are sent to technicians when storage conditions deviate from the optimal range.

### 📲 **Multiple Payment Options**
Supports RFID card payments, QR codes, and future payment integrations.

---

## 🛠 Future Enhancements
- **Integration with an online payment gateway**
- **IoT-based remote monitoring system**
- **Automated restocking notifications**
- **AI-powered predictive maintenance**

---

## User Guide
### 1. Database Setup
  - Open the system-wide environment file:
      *sudo nano/etc/environment*
  - Add this at the end of the file (without export):
      *DB_PATH="/home/pi/user's custom naming directory/src/sqlite-data/vending_machine.db"*
  - Save `(CTRL+X)`, then `Y`, then `Enter`.
  - Reboot for changes to take effect.
      *sudo reboot*
  - If you run echo $DB_PATH on terminal,
      */home/pi/user's custom naming directory/src/sqlite-data/vending_machine.db" will appear.*
  - Run initialize_database.py
  - Run insert_user.py
  - Run generate_data.py (optional if you want extra data)

### 2. Running Docker
  - *docker build -t vending-app-f Dockerfile-app .*
  - *docker run -d --name vending-app -p 5000:5000 \
    --env-file ../.env \
    -v /home/pi/alvin/DevOps/src/sqlite-data:/sqlite-data \
    -v /home/pi/alvin/DevOps/src/qrcodes:/app/qrcodes \
    kinda1vin/vending-app:latest*

### 3. Run admin.py for admin server
### 4. Run app.py for remote order system from website
  - Customer will be able to order drink from website and purchase by card and apple pay.
  - After payment is confirmed, QR code for drink collection will be sent to customer.
### 5. Run telegram_bot.py
### 6. Run main.py.
  - LCD displays main menu. 1. Admin, 2. Customer
    - Customer
      - Two options. 1. order, 2. pick-up. 
      - To order drink, select drink by pressing number (press # to enter) on keypad. LCD will display the drink order.
      - Customer can purchase either by rfid card, or qr code.
      - After confiming order, drink preparation takes place, and the door will be opened for drinks collection.
      - For remote orders, select pick-up, and scan the qr code sent in telegram. After scanning qr code, the door will open.
    - Admin
      - Enter passcode (1234) and the door will open for admin.
    
---  

## Contribution
- **[KYAW NYI NYI HAN]** - Remote/ Local order system, Database Configuration and Maintenance, Website, Admin server, Docker, Debugging and Testing
- **[ALARCIO JAESON MATHEW BALICTAR]** -
- **[Su Myat Mon]** - Environmental Monitoring, Inventory Checking and Updating, Admin Server
- **[Wai Yan Min Khaung]** - Security Feature, Drink Preparation, Admin Log in, Debugging and Testing
      
## 🤝 Contributors

- **[KYAW NYI NYI HAN]** 
- **[ALARCIO JAESON MATHEW BALICTAR ]** 
- **[SU MYAT MON]** 
- **[WAI YAN MIN KHAUNG]** 


---
