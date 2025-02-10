#!/usr/bin/env python3
import os
import time
import logging
import asyncio
import threading
from telegram import Bot
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Use your provided Telegram bot token.
TELEGRAM_BOT_TOKEN = "7854261569:AAHLf1DASQHn1MBiryaxGuEcaJtephX8d7M"
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Define the QR codes folder (must match the one used in payment_app.py)
QR_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qrcodes")
if not os.path.exists(QR_FOLDER):
    os.makedirs(QR_FOLDER)

def parse_chat_id_from_filename(filename):
    """
    Expected filename format: "qr_<chat_id>_<transaction_id>.png"
    Extracts and returns the chat_id as an integer.
    """
    try:
        parts = filename.split('_')
        if len(parts) < 3:
            logger.error("Filename %s does not have enough parts.", filename)
            return None
        chat_id_str = parts[1]
        chat_id = int(chat_id_str)
        logger.info("Parsed chat_id %s from filename %s", chat_id, filename)
        return chat_id
    except Exception as e:
        logger.error("Error parsing chat id from filename %s: %s", filename, e)
        return None

# --- Set up a dedicated event loop in a background thread ---
def start_event_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

# Create a new event loop and start it in a daemon thread.
event_loop = asyncio.new_event_loop()
loop_thread = threading.Thread(target=start_event_loop, args=(event_loop,), daemon=True)
loop_thread.start()
logger.info("Started dedicated asyncio event loop in background thread.")

class QRFileHandler(PatternMatchingEventHandler):
    patterns = ["*.png"]  # Watch for PNG files

    def on_created(self, event):
        if event.is_directory:
            return
        file_path = event.src_path
        filename = os.path.basename(file_path)
        logger.info("New QR file detected: %s", filename)
        chat_id = parse_chat_id_from_filename(filename)
        if chat_id is None:
            logger.error("Could not parse chat id from filename: %s", filename)
            return

        async def send_photo_async():
            try:
                # Open the file and send the photo using the bot.
                with open(file_path, 'rb') as photo:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption="Here is your QR code for payment."
                    )
                logger.info("Sent QR code %s to chat %s", filename, chat_id)
                # Delete the file after successful sending.
                os.remove(file_path)
                logger.info("Deleted QR file %s after sending", filename)
            except Exception as e:
                logger.error("Error sending QR code %s: %s", filename, e)

        # Schedule the async task on the dedicated event loop.
        future = asyncio.run_coroutine_threadsafe(send_photo_async(), event_loop)
        try:
            # Optionally wait for a short timeout to catch errors.
            future.result(timeout=30)
        except Exception as e:
            logger.error("Error running send_photo_async for %s: %s", filename, e)

def start_watcher():
    """
    Start the watchdog observer to monitor the QR folder.
    """
    event_handler = QRFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path=QR_FOLDER, recursive=False)
    observer.start()
    logger.info("Started QR folder watcher on %s", QR_FOLDER)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_watcher()
