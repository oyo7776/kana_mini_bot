import os
import threading
from flask import Flask
from telebot import TeleBot, types

# 🔑 Load bot token from Railway environment
BOT_TOKEN = os.environ.get("BOT_TOKEN")

bot = TeleBot(BOT_TOKEN)
app = Flask(__name__)

# 🟢 Mini App frontend link (your Railway link)
FRONTEND_URL = "https://kanaminibot-production.up.railway.app/"

# ✅ Flask route
@app.route('/')
def home():
    return "✅ Bot is running on Railway with Flask keep-alive!"

# 🎯 Start command
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton(
        "🚀 Open Mini App",
        web_app=types.WebAppInfo(FRONTEND_URL)
    )
    markup.add(btn)
    bot.send_message(
        message.chat.id,
        "Welcome! Click below to open the Mini App 👇",
        reply_markup=markup
    )

# 🟢 Run bot polling in background
def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    # Start bot in separate thread
    threading.Thread(target=run_bot).start()

    # Start Flask
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
