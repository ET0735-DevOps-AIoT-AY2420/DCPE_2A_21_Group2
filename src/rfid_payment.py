#!/usr/bin/env python
# -*- coding: utf8 -*-
#
#    Copyright 2014,2018 Mario Gomez <mario.gomez@teubi.co>
#
#    This file is part of MFRC522-Python
#    MFRC522-Python is a simple Python implementation for
#    the MFRC522 NFC Card Reader for the Raspberry Pi.
#
#    MFRC522-Python is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    MFRC522-Python is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with MFRC522-Python.  If not, see <http://www.gnu.org/licenses/>.
#

import RPi.GPIO as GPIO
import spi
import signal
import time
import uuid
import qrcode

# We'll also need these for our payment simulation:
import sys

# Global variable for the simulated RFID balance (in dollars)
rfid_balance = 100.0

class MFRC522:
    NRSTPD = 11
    MAX_LEN = 16

    PCD_IDLE       = 0x00
    PCD_AUTHENT    = 0x0E
    PCD_RECEIVE    = 0x08
    PCD_TRANSMIT   = 0x04
    PCD_TRANSCEIVE = 0x0C
    PCD_RESETPHASE = 0x0F
    PCD_CALCCRC    = 0x03

    PICC_REQIDL    = 0x26
    PICC_REQALL    = 0x52
    PICC_ANTICOLL  = 0x93
    PICC_SElECTTAG = 0x93
    PICC_AUTHENT1A = 0x60
    PICC_AUTHENT1B = 0x61
    PICC_READ      = 0x30
    PICC_WRITE     = 0xA0
    PICC_DECREMENT = 0xC0
    PICC_INCREMENT = 0xC1
    PICC_RESTORE   = 0xC2
    PICC_TRANSFER  = 0xB0
    PICC_HALT      = 0x50

    MI_OK       = 0
    MI_NOTAGERR = 1
    MI_ERR      = 2

    # Register addresses and other constants omitted for brevity...
    CommandReg     = 0x01
    CommIEnReg     = 0x02
    DivIrqReg      = 0x05
    ErrorReg       = 0x06
    Status2Reg     = 0x08
    FIFODataReg    = 0x09
    FIFOLevelReg   = 0x0A
    ControlReg     = 0x0C
    BitFramingReg  = 0x0D
    TxControlReg   = 0x14
    ModeReg        = 0x11
    TModeReg       = 0x2A
    TPrescalerReg  = 0x2B
    TReloadRegL    = 0x2D
    TReloadRegH    = 0x2C
    TxAutoReg      = 0x15

    def __init__(self, dev='/dev/spidev0.1', spd=1000000):
        global spidev
        spidev = spi.openSPI(device=dev, speed=spd)
        GPIO.setmode(GPIO.BCM)
        self.MFRC522_Init()

    def MFRC522_Reset(self):
        self.Write_MFRC522(self.CommandReg, self.PCD_RESETPHASE)

    def Write_MFRC522(self, addr, val):
        spi.transfer(spidev, ((addr<<1)&0x7E, val))

    def Read_MFRC522(self, addr):
        val = spi.transfer(spidev, (((addr<<1)&0x7E)|0x80, 0))
        return val[1]

    def SetBitMask(self, reg, mask):
        tmp = self.Read_MFRC522(reg)
        self.Write_MFRC522(reg, tmp | mask)

    def ClearBitMask(self, reg, mask):
        tmp = self.Read_MFRC522(reg)
        self.Write_MFRC522(reg, tmp & (~mask))

    def AntennaOn(self):
        temp = self.Read_MFRC522(self.TxControlReg)
        if (~(temp & 0x03)):
            self.SetBitMask(self.TxControlReg, 0x03)

    def AntennaOff(self):
        self.ClearBitMask(self.TxControlReg, 0x03)

    # MFRC522_ToCard, MFRC522_Request, MFRC522_Anticoll, CalulateCRC,
    # MFRC522_SelectTag, MFRC522_Auth, MFRC522_StopCrypto1, MFRC522_Read,
    # MFRC522_Write, etc.
    # (Omitted here for brevity; use the existing methods from your code.)
    # ...

    def MFRC522_Init(self):
        self.MFRC522_Reset()
        self.Write_MFRC522(self.TModeReg, 0x8D)
        self.Write_MFRC522(self.TPrescalerReg, 0x3E)
        self.Write_MFRC522(self.TReloadRegL, 30)
        self.Write_MFRC522(self.TReloadRegH, 0)
        self.Write_MFRC522(self.TxAutoReg, 0x40)
        self.Write_MFRC522(self.ModeReg, 0x3D)
        self.AntennaOn()


# A simplified wrapper for easier use.
class SimpleMFRC522:
    READER = None
    KEY = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
    BLOCK_ADDRS = [8, 9, 10]

    def __init__(self):
        self.READER = MFRC522()

    def read(self):
        id, text = self.read_no_block()
        while not id:
            id, text = self.read_no_block()
        return id, text

    def read_id(self):
        id = self.read_id_no_block()
        while not id:
            id = self.read_id_no_block()
        return id

    def read_id_no_block(self):
        (status, TagType) = self.READER.MFRC522_Request(self.READER.PICC_REQIDL)
        if status != self.READER.MI_OK:
            return None
        (status, uid) = self.READER.MFRC522_Anticoll()
        if status != self.READER.MI_OK:
            return None
        return self.uid_to_num(uid)

    def read_no_block(self):
        (status, TagType) = self.READER.MFRC522_Request(self.READER.PICC_REQIDL)
        if status != self.READER.MI_OK:
            return None, None
        (status, uid) = self.READER.MFRC522_Anticoll()
        if status != self.READER.MI_OK:
            return None, None
        id = self.uid_to_num(uid)
        self.READER.MFRC522_SelectTag(uid)
        status = self.READER.MFRC522_Auth(self.READER.PICC_AUTHENT1A, 11, self.KEY, uid)
        data = []
        text_read = ''
        if status == self.READER.MI_OK:
            for block_num in self.BLOCK_ADDRS:
                block = self.READER.MFRC522_Read(block_num)
                if block:
                    data += block
            if data:
                text_read = ''.join(chr(i) for i in data)
        self.READER.MFRC522_StopCrypto1()
        return id, text_read

    def write(self, text):
        id, text_in = self.write_no_block(text)
        while not id:
            id, text_in = self.write_no_block(text)
        return id, text_in

    def write_no_block(self, text):
        (status, TagType) = self.READER.MFRC522_Request(self.READER.PICC_REQIDL)
        if status != self.READER.MI_OK:
            return None, None
        (status, uid) = self.READER.MFRC522_Anticoll()
        if status != self.READER.MI_OK:
            return None, None
        id = self.uid_to_num(uid)
        self.READER.MFRC522_SelectTag(uid)
        status = self.READER.MFRC522_Auth(self.READER.PICC_AUTHENT1A, 11, self.KEY, uid)
        self.READER.MFRC522_Read(11)
        if status == self.READER.MI_OK:
            data = bytearray()
            data.extend(bytearray(text.ljust(len(self.BLOCK_ADDRS) * 16).encode('ascii')))
            i = 0
            for block_num in self.BLOCK_ADDRS:
                self.READER.MFRC522_Write(block_num, data[(i * 16):(i + 1) * 16])
                i += 1
        self.READER.MFRC522_StopCrypto1()
        return id, text[0:(len(self.BLOCK_ADDRS) * 16)]

    def uid_to_num(self, uid):
        n = 0
        for i in range(0, 5):
            n = n * 256 + uid[i]
        return n

def init():
    rfid_reader = SimpleMFRC522()
    return rfid_reader

# --- Payment Simulation Using RFID ---

def simulate_rfid_payment(payment_amount=2.50):
    """
    Simulate a payment using RFID:
      - Wait for a card to be scanned.
      - Deduct the payment amount from a simulated balance (rfid_balance).
      - Print out the result.
    """
    global rfid_balance
    reader = init()
    print("Please scan your RFID card for a payment of ${:.2f}...".format(payment_amount))
    card_id, text = reader.read()  # This call blocks until a card is detected.
    print("Card detected! Card ID:", card_id)
    if rfid_balance >= payment_amount:
        rfid_balance -= payment_amount
        print("Payment of ${:.2f} processed successfully.".format(payment_amount))
        print("New balance: ${:.2f}".format(rfid_balance))
    else:
        print("Insufficient funds for payment!")
    # You can return values or log them as needed.
    return card_id, rfid_balance

if __name__ == "__main__":
    try:
        while True:
            simulate_rfid_payment(payment_amount=2.50)
            print("\nWaiting for the next payment... (Press Ctrl+C to exit)")
            time.sleep(2)  # Pause briefly before the next cycle.
    except KeyboardInterrupt:
        print("RFID payment simulation terminated.")
        GPIO.cleanup()
        sys.exit(0)
