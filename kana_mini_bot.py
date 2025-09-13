import os
from flask import Flask
from telebot import TeleBot, types

# 🔑 Your Telegram bot token (set in Railway variables)
BOT_TOKEN = os.environ.get("BOT_TOKEN")

bot = TeleBot(BOT_TOKEN)
app = Flask(__name__)

# 🟢 Mini App frontend link (your Railway web domain)
FRONTEND_URL = "kanaminibot-production.up.railway.app"

# ✅ Flask home route for Railway keep-alive
@app.route('/')
def home():
    return "✅ Bot is running on Railway with Flask keep-alive!"

# 🎯 Telegram bot command
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

# 🟢 Keep bot alive with polling
def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    # Run Flask (Railway exposes this)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
