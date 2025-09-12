from flask import Flask, render_template
import telebot, os, threading

BOT_TOKEN = os.getenv("BOT_TOKEN")  # set in Railway later
bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

# Serve Mini App
@app.route("/")
def index():
    return render_template("index.html")

# Telegram /start
@bot.message_handler(commands=["start"])
def send_welcome(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    webAppTest = telebot.types.WebAppInfo("https://YOUR-RAILWAY-URL/")  
    markup.add(telebot.types.KeyboardButton("🎮 Open Mini App", web_app=webAppTest))
    bot.send_message(message.chat.id, "✅ Welcome! Open the Mini App:", reply_markup=markup)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))).start()
    bot.polling(none_stop=True)
