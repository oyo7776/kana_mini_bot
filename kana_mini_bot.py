import os
import sqlite3
import random
import requests
import telebot
from flask import Flask, request, jsonify
import threading

# ----- ENV VARIABLES -----
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAPA_SECRET_KEY = os.getenv("CHAPA_SECRET_KEY")

bot = telebot.TeleBot(BOT_TOKEN)

# ----- DATABASE -----
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    type TEXT,
    amount REAL,
    status TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    game TEXT,
    amount REAL,
    multiplier REAL,
    status TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)""")
conn.commit()

# ----- HELPERS -----
def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    if not result:
        cursor.execute("INSERT INTO users(user_id) VALUES(?)", (user_id,))
        conn.commit()
        return 0
    return result[0]

def update_balance(user_id, amount):
    balance = get_balance(user_id) + amount
    cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (balance, user_id))
    conn.commit()
    return balance

def create_chapa_payment(amount, email):
    url = "https://api.chapa.co/v1/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {CHAPA_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "amount": str(amount),
        "currency": "ETB",
        "email": email,
        "first_name": "User",
        "last_name": "Test",
        "tx_ref": "tx-" + os.urandom(6).hex(),
        "callback_url": "https://yourapp.up.railway.app/webhook",
        "return_url": "https://t.me/YOURBOTNAME"
    }
    response = requests.post(url, headers=headers, json=data).json()
    return response

# ----- TELEGRAM BOT -----
@bot.message_handler(commands=['start'])
def start(message):
    balance = get_balance(message.chat.id)
    bot.send_message(message.chat.id, f"Welcome! Your balance: {balance} ETB")

@bot.message_handler(commands=['balance'])
def balance_cmd(message):
    balance = get_balance(message.chat.id)
    bot.send_message(message.chat.id, f"Your balance: {balance} ETB")

@bot.message_handler(commands=['deposit'])
def deposit_cmd(message):
    try:
        parts = message.text.split()
        amount = float(parts[1])
        email = parts[2]
        payment = create_chapa_payment(amount, email)
        bot.send_message(message.chat.id, f"Pay here: {payment['data']['checkout_url']}")
    except:
        bot.send_message(message.chat.id, "Usage: /deposit <amount> <email>")

@bot.message_handler(commands=['bet'])
def bet_cmd(message):
    try:
        parts = message.text.split()
        game = parts[1].lower()
        amount = float(parts[2])
        balance = get_balance(message.chat.id)
        if amount > balance:
            bot.send_message(message.chat.id, "Insufficient balance!")
            return

        multiplier = round(random.uniform(1.0, 5.0), 2)
        won_amount = round(amount * multiplier, 2)
        result = random.choice(["won", "lost"])

        if result == "won":
            update_balance(message.chat.id, won_amount)
            status = "won"
            bot.send_message(message.chat.id, f"You won {won_amount} ETB! Multiplier: x{multiplier}")
        else:
            update_balance(message.chat.id, -amount)
            status = "lost"
            bot.send_message(message.chat.id, f"You lost {amount} ETB! Multiplier: x{multiplier}")

        cursor.execute("INSERT INTO bets(user_id, game, amount, multiplier, status) VALUES (?,?,?,?,?)",
                       (message.chat.id, game, amount, multiplier, status))
        conn.commit()
    except:
        bot.send_message(message.chat.id, "Usage: /bet <game> <amount>")

# ----- WITHDRAW -----
@bot.message_handler(commands=['withdraw'])
def withdraw_cmd(message):
    try:
        parts = message.text.split()
        amount = float(parts[1])
        email = parts[2]
        balance = get_balance(message.chat.id)
        if amount > balance:
            bot.send_message(message.chat.id, "Insufficient balance!")
            return

        headers = {
            "Authorization": f"Bearer {CHAPA_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "amount": str(amount),
            "currency": "ETB",
            "email": email,
            "tx_ref": "wd-" + os.urandom(6).hex()
        }
        response = requests.post("https://api.chapa.co/v1/payout", headers=headers, json=data).json()

        if response.get("status") == "success":
            update_balance(message.chat.id, -amount)
            cursor.execute("INSERT INTO transactions(user_id, type, amount, status) VALUES (?,?,?,?)",
                           (message.chat.id, "withdraw", amount, "success"))
            conn.commit()
            bot.send_message(message.chat.id, f"Withdrawal of {amount} ETB successful!")
        else:
            bot.send_message(message.chat.id, "Withdrawal failed. Contact admin.")
    except:
        bot.send_message(message.chat.id, "Usage: /withdraw <amount> <email>")

# ----- FLASK APP -----
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def chapa_webhook():
    data = request.json
    status = data.get("status")
    amount = float(data.get("amount", 0))
    user_id = data.get("user_id")

    if status == "success" and user_id:
        update_balance(user_id, amount)
        cursor.execute("INSERT INTO transactions(user_id, type, amount, status) VALUES (?,?,?,?)",
                       (user_id, "deposit", amount, "success"))
        conn.commit()
        return jsonify({"status": "ok"}), 200

    return jsonify({"status": "ignored"}), 200

# ----- START BOTH -----
def run_bot():
    bot.infinity_polling()

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    run_flask()
