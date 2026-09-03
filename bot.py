import os
import subprocess
import tempfile
import glob
import time
import shutil
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
    bot.reply_to(m, "Bhejo 1 hour episode! Mai 30 sec clips + ZIP dunga.")

@bot.message_handler(content_types=['video', 'document'])
def handle_video(m):
    try:
        file_id = m.video.file_id if m.video else m.document.file_id
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        with tempfile.TemporaryDirectory() as tmp:
            in_path = os.path.join(tmp, "ep.mp4")
            with open(in_path, "wb") as f:
                f.write(downloaded)
            pattern = os.path.join(tmp, "clip_%03d.mp4")
            cmd = ["ffmpeg", "-y", "-i", in_path, "-c", "copy", "-map", "0", "-segment_time", "30", "-f", "segment", "-reset_timestamps", "1", pattern]
            subprocess.run(cmd, check=True)
            clips = sorted(glob.glob(os.path.join(tmp, "clip_*.mp4")))
            bot.send_message(m.chat.id, f"Total {len(clips)} clips")
            zip_base = os.path.join(tmp, "all_clips")
            shutil.make_archive(zip_base, 'zip', tmp)
            with open(zip_base + ".zip", "rb") as z:
                bot.send_document(m.chat.id, z)
            for i, clip_path in enumerate(clips):
                with open(clip_path, "rb") as c:
                    bot.send_video(m.chat.id, c, caption=f"Clip {i+1}/{len(clips)}")
                if (i+1) % 20 == 0:
                    time.sleep(2)
            bot.send_message(m.chat.id, "Done!")
    except Exception as e:
        bot.reply_to(m, f"Error: {e}")

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
