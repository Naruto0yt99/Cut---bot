from flask import Flask
import threading
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

app_flask = Flask('')
@app_flask.route('/')
def home(): return "Bot Alive!"
threading.Thread(target=lambda: app_flask.run(host='0.0.0.0', port=10000)).start()

BOT_TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bhejo video, mai cut karke dunga!")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Video mil gaya! Processing...")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.VIDEO, handle_video))
app.run_polling()
