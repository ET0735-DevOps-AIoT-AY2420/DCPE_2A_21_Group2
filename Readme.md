# Smart Drink Vending Machine

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

## 🤝 Contributors

- **[KYAW NYI NYI HAN]** 
- **[ALARCIO JAESON MATHEW BALICTAR ]** 
- **[SU MYAT MON]** 
- **[WAI YAN MIN KHAUNG]** 


---
