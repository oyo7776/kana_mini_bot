import os
import telebot
import threading
import random
from flask import Flask

# --- Telegram Bot ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# --- Games ---
@bot.message_handler(commands=["start"])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎮 Play Aviator", "🎮 Play Dice")
    bot.send_message(message.chat.id, "Welcome! Choose a game:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "🎮 Play Aviator")
def aviator(message):
    multiplier = round(random.uniform(1.1, 10.0), 2)
    bot.send_message(message.chat.id, f"✈️ Aviator took off!\nMultiplier: {multiplier}x")

@bot.message_handler(func=lambda msg: msg.text == "🎮 Play Dice")
def dice(message):
    roll = random.randint(1, 6)
    bot.send_message(message.chat.id, f"🎲 You rolled a {roll}")

def run_bot():
    bot.polling(non_stop=True)

# --- Flask Keep-Alive ---
app = Flask(__name__)

@app.route("/")
def home():
    return "Kana Mini Bot with Games ✅"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# --- Run both (bot + Flask) ---
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    run_flask()
