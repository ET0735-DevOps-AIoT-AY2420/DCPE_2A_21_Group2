from picamera2.encoders import H264Encoder
from picamera2 import Picamera2, Preview
import time
import os
from datetime import datetime
from telegram import Bot
import subprocess 

# Initialize the camera
picam2 = Picamera2()
latest_video_path = None
BOT_TOKEN = "7723998968:AAFc4QK-qRaIxCfqeqLYRs1OLuF-2z_OOiM"
CHAT_ID = "5819192033"

bot = Bot(token=BOT_TOKEN)

# Create the video configuration
video_config = picam2.create_video_configuration(
        main={"size": (1920, 1080)},
        lores={"size": (640, 480)},
        display="lores"
    )
picam2.configure(video_config)

# Create the encoder
encoder = H264Encoder(bitrate=10000000)

def send_latest_video():
    global latest_video_path
    if latest_video_path and os.path.exists(latest_video_path):
        try:
            with open(latest_video_path, "rb") as video:
                bot.send_video(chat_id=CHAT_ID, video=video, caption="Security Alert: Latest video recorded.")
            print(f"Telegram video sent: {latest_video_path}")
        except Exception as e:
            print(f"Error sending Telegram video: {e}")
    else:
        print("No video found to send.")


def take_videos(duration=10, output_dir="/home/pi/wanyay/src/videos"):

    global latest_video_path
    # Generate a unique filename using the current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    h264_path = os.path.join(output_dir, f"video_{timestamp}.h264")
    mp4_path = os.path.join(output_dir, f"video_{timestamp}.mp4")

    try:
        # Start the preview (use Preview.NULL for headless setup)
        picam2.start_preview(Preview.NULL)
    except Exception as e:
        print(f"Preview initialization error: {e}")

    try:
        # Start recording
        picam2.start_recording(encoder, h264_path)

        # Record for the specified duration
        time.sleep(duration)

        # Stop recording
        picam2.stop_recording()
        picam2.stop_preview()

        print(f"Video saved to: {h264_path}")

        # Convert .h264 to .mp4
        convert_to_mp4(h264_path, mp4_path)
        latest_video_path = mp4_path  # Update the global variable to the .mp4 file

    except Exception as e:
        print(f"Error during recording: {e}")

def convert_to_mp4(h264_path, mp4_path):
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-framerate", "30", "-i", h264_path, "-c:v", "copy", mp4_path],
            check=True
        )
        print(f"Converted {h264_path} to {mp4_path}")
    except Exception as e:
        print(f"Error converting video: {e}")
