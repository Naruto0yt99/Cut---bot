import os
import subprocess
import tempfile
import glob
import time
import shutil
import zipfile
from flask import Flask
import telebot
from threading import Thread

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route('/')
def alive():
    return "1-Hour Splitter Ready - 30sec Clips"

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "Bhejo 1 hour ka episode! 🎬\nMai isko 30-30 sec ke clips me tod ke ZIP me dunga.")

@bot.message_handler(content_types=['video', 'document'])
def handle_video(m):
    try:
        bot.reply_to(m, "Downloading... ⏳ 1 hour video hai to 1-2 min lagega")
        file_id = m.video.file_id if m.video else m.document.file_id
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.mp4")
            with open(input_path, 'wb') as f:
                f.write(downloaded)

            # Duration nikalo
            try:
                result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", input_path], capture_output=True, text=True)
                duration = float(result.stdout.strip())
            except:
                duration = 3600 # fallback 1 hour

            bot.reply_to(m, f"Video mil gaya {int(duration)} sec ka. Ab 30sec clips bana raha hu... ✂️")

            clips_dir = os.path.join(tmpdir, "clips")
            os.makedirs(clips_dir, exist_ok=True)

            clip_paths = []
            start_time = 0
            clip_num = 1
            while start_time < duration:
                out_path = os.path.join(clips_dir, f"clip_{clip_num:03d}.mp4")
                # re-encode for perfect