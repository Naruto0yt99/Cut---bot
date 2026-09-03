import os, subprocess, tempfile, glob, time, shutil
from flask import Flask
import telebot
from threading import Thread

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route('/')
def alive():
    return "1-Hour Splitter Ready"

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "Bhejo 1 hour tak ki episode!\nMai 30 sec ke clips bana ke ZIP + alag-alag bhi bhejunga.\nMax: 1GB tak")

@bot.message_handler(content_types=['video', 'document'])
def handle_video(m):
    try:
        size = m.video.file_size if m.video else m.document.file_size
        mb = size//(1024*1024)
        
        bot.reply_to(m, f"Mil gaya {mb}MB ka Episode!\nProcessing start... {mb//10} min lag sakta hai 1 hour ke liye ⏳")

        file_id = m.video.file_id if m.video else m.document.file_id
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        with tempfile.TemporaryDirectory() as tmp:
            in_path = os.path.join(tmp, "ep.mp4")
            with open(in_path, "wb") as f:
                f.write(downloaded)

            pattern = os.path.join(tmp, "clip_%03d.mp4")
            cmd = ["ffmpeg", "-y", "-i", in_path, "-c", "copy", "-map", "0", "-segment_time", "30", "-f", "segment", "-reset_timestamps", "1", pattern]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            clips = sorted(glob.glob(os.path.join(tmp, "clip_*.mp4")))
            bot.send_message(m.chat.id, f"Total {len(clips)} clips bane! ({len(clips)*30//60} min ki video)\nAb bhej raha hu, har 10 clips ke baad 3 sec rukunga.")

            # 1. ZIP banao
            zip_path = os.path.join(tmp, "all_clips.zip")
            with tempfile.TemporaryDirectory() as zip_tmp:
                # just to create zip of clips
                shutil.make_archive(os.path.join(tmp, "all_clips"), 'zip', tmp, pattern="clip_*.mp4")
            
            with open(zip_path, "rb") as z:
                bot.send_document(m.chat.id, z, caption=f"ZIP me {len(clips)} clips hai! 📦")

            # 2. Alag-alag bhe
