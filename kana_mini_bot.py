import os
from flask import Flask
import telebot

# Get your bot token from Railway variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Flask route for Railway keep-alive
@app.route("/")
def home():
    return "✅ Bot is running on Railway with Flask keep-alive!"

# Telegram command
@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(message, "Hello 👋, your bot is live on Railway!")

if __name__ == "__main__":
    # Start Flask server
    port = int(os.environ.get("PORT", 5000))
    from threading import Thread

    def run_flask():
        app.run(host="0.0.0.0", port=port)

    def run_bot():
        bot.infinity_polling()

    # Run both Flask + Bot
    Thread(target=run_flask).start()
    Thread(target=run_bot).start()
