import os
import telebot
import threading
from flask import Flask

# --- Telegram Bot ---
BOT_TOKEN = os.getenv("BOT_TOKEN")  # get token from Railway variables
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "✅ Bot is running on Railway with Flask keep-alive!")

def run_bot():
    bot.polling(non_stop=True)

# --- Flask Keep-Alive ---
app = Flask(__name__)

@app.route("/")
def home():
    return "Kana Mini Bot is running ✅"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# --- Run both (bot + Flask) ---
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    run_flask()
